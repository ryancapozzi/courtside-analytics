from __future__ import annotations

from .types import IntentType, ResolvedContext, SQLPlan


class TemplateSQLBuilder:
    def build(self, intent: IntentType, context: ResolvedContext) -> SQLPlan | None:
        if intent == IntentType.CONDITIONAL_TEAM_PERFORMANCE:
            return self._build_conditional_team_performance(context)

        if intent == IntentType.TEAM_COMPARISON:
            return self._build_team_comparison(context)

        if intent == IntentType.TEAM_TREND:
            return self._build_team_trend(context)

        if intent == IntentType.PLAYER_RANKING:
            return self._build_player_ranking(context)

        return None

    def _build_conditional_team_performance(self, context: ResolvedContext) -> SQLPlan | None:
        if not context.teams or not context.players:
            return None

        team = context.teams[0]
        player = context.players[0]

        points_threshold = context.thresholds.get("points_more_than")
        if points_threshold is None:
            points_threshold = context.thresholds.get("points_over", 25)

        sql = """
        SELECT
          t.team_name,
          p.player_name,
          COUNT(*) AS games,
          SUM(CASE WHEN tgr.is_win = 1 THEN 1 ELSE 0 END) AS wins,
          ROUND(AVG(tgr.is_win::numeric) * 100, 2) AS win_pct,
          ROUND(AVG(pgs.points)::numeric, 2) AS avg_player_points,
          ROUND(AVG(tgr.team_points)::numeric, 2) AS avg_team_points
        FROM player_game_stats pgs
        JOIN games g ON g.game_id = pgs.game_id
        JOIN team_game_results tgr ON tgr.game_id = g.game_id AND tgr.team_id = pgs.team_id
        JOIN teams t ON t.team_id = pgs.team_id
        JOIN players p ON p.player_id = pgs.player_id
        WHERE pgs.player_id = %s
          AND pgs.team_id = %s
          AND pgs.points > %s
        GROUP BY t.team_name, p.player_name;
        """

        return SQLPlan(
            sql=sql,
            params=(player.id, team.id, points_threshold),
            source="template",
            notes=[f"Using threshold points > {points_threshold}"],
        )

    def _build_team_comparison(self, context: ResolvedContext) -> SQLPlan | None:
        if len(context.teams) < 2:
            return None

        team_a = context.teams[0]
        team_b = context.teams[1]

        sql = """
        SELECT
          s.season_label,
          t.team_name,
          COUNT(*) AS games,
          SUM(CASE WHEN tgr.is_win = 1 THEN 1 ELSE 0 END) AS wins,
          ROUND(AVG(tgr.is_win::numeric) * 100, 2) AS win_pct,
          ROUND(AVG(tgr.team_points)::numeric, 2) AS avg_points
        FROM team_game_results tgr
        JOIN games g ON g.game_id = tgr.game_id
        JOIN seasons s ON s.season_id = g.season_id
        JOIN teams t ON t.team_id = tgr.team_id
        WHERE tgr.team_id IN (%s, %s)
        GROUP BY s.start_year, s.season_label, t.team_name
        ORDER BY s.start_year, t.team_name;
        """

        return SQLPlan(
            sql=sql,
            params=(team_a.id, team_b.id),
            source="template",
            notes=[f"Comparing {team_a.name} vs {team_b.name}"],
        )

    def _build_team_trend(self, context: ResolvedContext) -> SQLPlan | None:
        if not context.teams:
            return None

        team = context.teams[0]

        sql = """
        SELECT
          s.season_label,
          COUNT(*) AS games,
          SUM(CASE WHEN tgr.is_win = 1 THEN 1 ELSE 0 END) AS wins,
          ROUND(AVG(tgr.is_win::numeric) * 100, 2) AS win_pct,
          ROUND(AVG(tgr.team_points)::numeric, 2) AS avg_points,
          ROUND(AVG(tgr.opponent_points)::numeric, 2) AS avg_points_allowed
        FROM team_game_results tgr
        JOIN games g ON g.game_id = tgr.game_id
        JOIN seasons s ON s.season_id = g.season_id
        WHERE tgr.team_id = %s
        GROUP BY s.start_year, s.season_label
        ORDER BY s.start_year;
        """

        return SQLPlan(
            sql=sql,
            params=(team.id,),
            source="template",
            notes=[f"Trend for {team.name}"],
        )

    def _build_player_ranking(self, context: ResolvedContext) -> SQLPlan:
        season_filter = ""
        params: list[object] = []

        if context.seasons:
            season_filter = "AND s.season_label = %s"
            params.append(context.seasons[0])

        sql = f"""
        SELECT
          p.player_name,
          COUNT(*) AS games,
          ROUND(AVG(pgs.points)::numeric, 2) AS avg_points,
          ROUND(AVG(pgs.assists)::numeric, 2) AS avg_assists,
          ROUND(AVG(pgs.rebounds)::numeric, 2) AS avg_rebounds
        FROM player_game_stats pgs
        JOIN players p ON p.player_id = pgs.player_id
        JOIN games g ON g.game_id = pgs.game_id
        JOIN seasons s ON s.season_id = g.season_id
        WHERE pgs.minutes IS NOT NULL
          {season_filter}
        GROUP BY p.player_name
        HAVING COUNT(*) >= 20
        ORDER BY avg_points DESC
        LIMIT 15;
        """

        return SQLPlan(
            sql=sql,
            params=tuple(params),
            source="template",
            notes=["Ranking query uses minimum 20 games played."],
        )
