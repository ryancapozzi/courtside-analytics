from __future__ import annotations

from .types import IntentType, ResolvedContext, SQLPlan


class TemplateSQLBuilder:
    def build(self, intent: IntentType, context: ResolvedContext) -> SQLPlan | None:
        if intent == IntentType.CONDITIONAL_TEAM_PERFORMANCE:
            return self._build_conditional_team_performance(context)

        if intent == IntentType.PLAYER_THRESHOLD_COUNT:
            return self._build_player_threshold_count(context)

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

        threshold_stat, threshold_operator, threshold_value = self._extract_threshold_filter(context)
        game_scope_clause, game_scope_note = self._scope_clause(context.game_scope)

        sql = f"""
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
          {game_scope_clause}
          AND pgs.{threshold_stat} {threshold_operator} %s
        GROUP BY t.team_name, p.player_name;
        """

        return SQLPlan(
            sql=sql,
            params=(player.id, team.id, threshold_value),
            source="template",
            notes=[
                f"Using threshold {threshold_stat} {threshold_operator} {threshold_value}",
                game_scope_note,
            ],
        )

    def _build_player_threshold_count(self, context: ResolvedContext) -> SQLPlan | None:
        if not context.players:
            return None

        player = context.players[0]
        threshold_stat, threshold_operator, threshold_value = self._extract_threshold_filter(context)
        game_scope_clause, game_scope_note = self._scope_clause(context.game_scope)

        team_clause = ""
        team_note = "Team scope: all teams."
        params: list[object] = [threshold_value, player.id]

        if context.teams:
            team = context.teams[0]
            team_clause = "AND pgs.team_id = %s"
            params.append(team.id)
            team_note = f"Team scope: {team.name}."

        season_clause = ""
        season_note = "Season scope: all available seasons."
        if context.seasons:
            season_clause = "AND s.season_label = %s"
            params.append(context.seasons[0])
            season_note = f"Season scope: {context.seasons[0]}."

        params.append(threshold_value)

        sql = f"""
        SELECT
          p.player_name,
          '{threshold_stat}' AS threshold_stat,
          '{threshold_operator}' AS threshold_operator,
          %s::numeric AS threshold_value,
          COUNT(*) AS games_meeting_threshold,
          ROUND(AVG(pgs.{threshold_stat})::numeric, 2) AS avg_stat_value
        FROM player_game_stats pgs
        JOIN players p ON p.player_id = pgs.player_id
        JOIN games g ON g.game_id = pgs.game_id
        JOIN seasons s ON s.season_id = g.season_id
        WHERE pgs.player_id = %s
          {team_clause}
          {game_scope_clause}
          {season_clause}
          AND pgs.{threshold_stat} {threshold_operator} %s
        GROUP BY p.player_name;
        """

        return SQLPlan(
            sql=sql,
            params=tuple(params),
            source="template",
            notes=[
                f"Threshold count for {player.name}.",
                f"Using threshold {threshold_stat} {threshold_operator} {threshold_value}",
                game_scope_note,
                team_note,
                season_note,
            ],
        )

    def _build_team_comparison(self, context: ResolvedContext) -> SQLPlan | None:
        if len(context.teams) < 2:
            return None

        team_a = context.teams[0]
        team_b = context.teams[1]
        game_scope_clause, game_scope_note = self._scope_clause(context.game_scope)

        sql = f"""
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
          {game_scope_clause}
        GROUP BY s.start_year, s.season_label, t.team_name
        ORDER BY s.start_year, t.team_name;
        """

        return SQLPlan(
            sql=sql,
            params=(team_a.id, team_b.id),
            source="template",
            notes=[f"Comparing {team_a.name} vs {team_b.name}", game_scope_note],
        )

    def _build_team_trend(self, context: ResolvedContext) -> SQLPlan | None:
        if not context.teams:
            return None

        team = context.teams[0]
        game_scope_clause, game_scope_note = self._scope_clause(context.game_scope)

        sql = f"""
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
          {game_scope_clause}
        GROUP BY s.start_year, s.season_label
        ORDER BY s.start_year;
        """

        return SQLPlan(
            sql=sql,
            params=(team.id,),
            source="template",
            notes=[f"Trend for {team.name}", game_scope_note],
        )

    def _build_player_ranking(self, context: ResolvedContext) -> SQLPlan:
        season_filter = ""
        params: list[object] = []
        game_scope_clause, game_scope_note = self._scope_clause(context.game_scope)

        metric_map = {
            "points": ("avg_points", "AVG(pgs.points)"),
            "assists": ("avg_assists", "AVG(pgs.assists)"),
            "rebounds": ("avg_rebounds", "AVG(pgs.rebounds)"),
            "steals": ("avg_steals", "AVG(pgs.steals)"),
            "blocks": ("avg_blocks", "AVG(pgs.blocks)"),
        }
        order_alias, order_expr = metric_map.get(context.ranking_metric, metric_map["points"])

        if context.seasons:
            season_filter = "AND s.season_label = %s"
            params.append(context.seasons[0])

        sql = f"""
        SELECT
          p.player_name,
          COUNT(*) AS games,
          ROUND(AVG(pgs.points)::numeric, 2) AS avg_points,
          ROUND(AVG(pgs.assists)::numeric, 2) AS avg_assists,
          ROUND(AVG(pgs.rebounds)::numeric, 2) AS avg_rebounds,
          ROUND(({order_expr})::numeric, 2) AS metric_value
        FROM player_game_stats pgs
        JOIN players p ON p.player_id = pgs.player_id
        JOIN games g ON g.game_id = pgs.game_id
        JOIN seasons s ON s.season_id = g.season_id
        WHERE pgs.minutes IS NOT NULL
          {game_scope_clause}
          {season_filter}
        GROUP BY p.player_name
        HAVING COUNT(*) >= 20
        ORDER BY {order_alias} DESC
        LIMIT 15;
        """

        return SQLPlan(
            sql=sql,
            params=tuple(params),
            source="template",
            notes=[
                "Ranking query uses minimum 20 games played.",
                f"Ranking metric: {context.ranking_metric}",
                game_scope_note,
            ],
        )

    def _extract_threshold_filter(self, context: ResolvedContext) -> tuple[str, str, float]:
        comparator_map = {
            "more_than": ">",
            "over": ">",
            "above": ">",
            "greater_than": ">",
            "at_least": ">=",
            "less_than": "<",
            "under": "<",
            "exactly": "=",
        }
        metric_priority = ["points", "rebounds", "assists", "steals", "blocks"]
        for stat in metric_priority:
            for suffix, op in comparator_map.items():
                key = f"{stat}_{suffix}"
                if key in context.thresholds:
                    return stat, op, context.thresholds[key]
        return "points", ">", 25.0

    def _scope_clause(self, game_scope: str) -> tuple[str, str]:
        if game_scope == "all":
            return "AND 1=1", "Game scope: all games."
        if game_scope == "playoffs":
            return "AND g.game_type = 'playoffs'", "Game scope: playoffs."
        if game_scope == "preseason":
            return "AND g.game_type = 'preseason'", "Game scope: preseason."
        return "AND g.game_type = 'regular'", "Game scope: regular season (default)."
