from __future__ import annotations

from .query_spec import QueryFamily, QuerySpec
from .types import ResolvedContext, SQLPlan


class QuerySQLBuilder:
    def build(self, spec: QuerySpec, context: ResolvedContext) -> SQLPlan | None:
        if spec.family == QueryFamily.CONDITIONAL_TEAM_PERFORMANCE:
            return self._build_conditional_team_performance(spec, context)
        if spec.family == QueryFamily.PLAYER_THRESHOLD_COUNT:
            return self._build_player_threshold_count(spec, context)
        if spec.family == QueryFamily.PLAYER_STAT:
            return self._build_player_stat(spec, context)
        if spec.family == QueryFamily.PLAYER_SINGLE_GAME_HIGH:
            return self._build_player_single_game_high(spec, context)
        if spec.family == QueryFamily.PLAYER_RANKING:
            return self._build_player_ranking(spec, context)
        if spec.family == QueryFamily.TEAM_COMPARISON:
            return self._build_team_comparison(spec, context)
        if spec.family == QueryFamily.TEAM_TREND:
            return self._build_team_trend(spec, context)
        if spec.family == QueryFamily.TEAM_STAT:
            return self._build_team_stat(spec, context)
        if spec.family == QueryFamily.TEAM_HEAD_TO_HEAD:
            return self._build_team_head_to_head(spec, context)
        if spec.family == QueryFamily.TEAM_RANKING:
            return self._build_team_ranking(spec, context)
        return None

    def _build_conditional_team_performance(self, spec: QuerySpec, context: ResolvedContext) -> SQLPlan | None:
        if not context.teams or not context.players:
            return None
        if spec.threshold_stat is None or spec.threshold_operator is None or spec.threshold_value is None:
            return None

        team = context.teams[0]
        player = context.players[0]
        game_scope_clause, game_scope_note = self._scope_clause(spec.game_scope)
        season_clause, season_params, season_note = self._season_clause(context)

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
        JOIN seasons s ON s.season_id = g.season_id
        JOIN team_game_results tgr ON tgr.game_id = g.game_id AND tgr.team_id = pgs.team_id
        JOIN teams t ON t.team_id = pgs.team_id
        JOIN players p ON p.player_id = pgs.player_id
        WHERE pgs.player_id = %s
          AND pgs.team_id = %s
          {game_scope_clause}
          {season_clause}
          AND pgs.{spec.threshold_stat} {spec.threshold_operator} %s
        GROUP BY t.team_name, p.player_name;
        """

        return SQLPlan(
            sql=sql,
            params=(player.id, team.id, *season_params, spec.threshold_value),
            source="query_spec",
            notes=[
                f"Family: {spec.family.value}",
                f"Threshold: {spec.threshold_stat} {spec.threshold_operator} {spec.threshold_value}",
                game_scope_note,
                season_note,
            ],
        )

    def _build_player_threshold_count(self, spec: QuerySpec, context: ResolvedContext) -> SQLPlan | None:
        if not context.players:
            return None
        if spec.threshold_stat is None or spec.threshold_operator is None or spec.threshold_value is None:
            return None

        player = context.players[0]
        game_scope_clause, game_scope_note = self._scope_clause(spec.game_scope)
        season_clause, season_params, season_note = self._season_clause(context)

        params: list[object] = [spec.threshold_value, player.id]
        team_clause = ""
        team_note = "Team scope: all teams."
        if context.teams:
            team = context.teams[0]
            team_clause = "AND pgs.team_id = %s"
            params.append(team.id)
            team_note = f"Team scope: {team.name}."

        params.extend(season_params)
        params.append(spec.threshold_value)

        sql = f"""
        SELECT
          p.player_name,
          '{spec.threshold_stat}' AS threshold_stat,
          '{spec.threshold_operator}' AS threshold_operator,
          %s::numeric AS threshold_value,
          COUNT(*) AS games_meeting_threshold,
          ROUND(AVG(pgs.{spec.threshold_stat})::numeric, 2) AS avg_stat_value
        FROM player_game_stats pgs
        JOIN players p ON p.player_id = pgs.player_id
        JOIN games g ON g.game_id = pgs.game_id
        JOIN seasons s ON s.season_id = g.season_id
        WHERE pgs.player_id = %s
          {team_clause}
          {game_scope_clause}
          {season_clause}
          AND pgs.{spec.threshold_stat} {spec.threshold_operator} %s
        GROUP BY p.player_name;
        """

        return SQLPlan(
            sql=sql,
            params=tuple(params),
            source="query_spec",
            notes=[
                f"Family: {spec.family.value}",
                team_note,
                game_scope_note,
                season_note,
            ],
        )

    def _build_player_stat(self, spec: QuerySpec, context: ResolvedContext) -> SQLPlan | None:
        if not context.players:
            return None

        player = context.players[0]
        game_scope_clause, game_scope_note = self._scope_clause(spec.game_scope)
        season_clause, season_params, season_note = self._season_clause(context)
        params: list[object] = [player.id]

        team_clause = ""
        team_note = "Team scope: all teams."
        if context.teams and spec.against_mode:
            opponent = context.teams[0]
            team_clause = """
            AND (
              (g.home_team_id = pgs.team_id AND g.away_team_id = %s)
              OR (g.away_team_id = pgs.team_id AND g.home_team_id = %s)
            )
            """
            params.extend([opponent.id, opponent.id])
            team_note = f"Opponent scope: {opponent.name}."
        elif context.teams:
            team = context.teams[0]
            team_clause = "AND pgs.team_id = %s"
            params.append(team.id)
            team_note = f"Team scope: {team.name}."

        params.extend(season_params)

        notes = [
            f"Family: {spec.family.value}",
            team_note,
            game_scope_note,
            season_note,
        ]

        if spec.response_mode == "profile":
            if spec.group_by == "season":
                sql = self._player_profile_by_season_sql(team_clause, game_scope_clause, season_clause)
            else:
                sql = self._player_profile_sql(team_clause, game_scope_clause, season_clause)
            notes.append("Response mode: profile.")
            if spec.group_by != "none":
                notes.append(f"Grouping: {spec.group_by}.")
            return SQLPlan(
                sql=sql,
                params=tuple(params),
                source="query_spec",
                notes=notes,
            )

        metric = self._safe_player_metric(spec.metric)
        operation = self._safe_stat_operation(spec.operation)
        params = [metric, operation, player.id, *params[1:]]

        if spec.group_by == "season":
            sql = self._player_stat_by_season_sql(metric, operation, team_clause, game_scope_clause, season_clause)
        else:
            sql = self._player_stat_sql(metric, operation, team_clause, game_scope_clause, season_clause)

        notes.extend(
            [
                f"Metric: {metric}",
                f"Operation: {operation}",
            ]
        )
        if spec.group_by != "none":
            notes.append(f"Grouping: {spec.group_by}.")

        return SQLPlan(
            sql=sql,
            params=tuple(params),
            source="query_spec",
            notes=notes,
        )

    def _player_profile_sql(
        self,
        team_clause: str,
        game_scope_clause: str,
        season_clause: str,
    ) -> str:
        return f"""
        SELECT
          p.player_name,
          COUNT(*) AS games,
          ROUND(AVG(pgs.points)::numeric, 2) AS avg_points,
          ROUND(AVG(pgs.rebounds)::numeric, 2) AS avg_rebounds,
          ROUND(AVG(pgs.assists)::numeric, 2) AS avg_assists,
          ROUND(AVG(pgs.steals)::numeric, 2) AS avg_steals,
          ROUND(AVG(pgs.blocks)::numeric, 2) AS avg_blocks,
          ROUND(AVG(pgs.turnovers)::numeric, 2) AS avg_turnovers,
          ROUND(AVG(pgs.minutes)::numeric, 2) AS avg_minutes,
          ROUND(
            (SUM(COALESCE(pgs.fg_made, 0))::numeric / NULLIF(SUM(COALESCE(pgs.fg_attempts, 0)), 0)) * 100,
            2
          ) AS fg_pct,
          ROUND(
            (SUM(COALESCE(pgs.three_made, 0))::numeric / NULLIF(SUM(COALESCE(pgs.three_attempts, 0)), 0)) * 100,
            2
          ) AS three_pct,
          ROUND(
            (SUM(COALESCE(pgs.ft_made, 0))::numeric / NULLIF(SUM(COALESCE(pgs.ft_attempts, 0)), 0)) * 100,
            2
          ) AS ft_pct
        FROM player_game_stats pgs
        JOIN players p ON p.player_id = pgs.player_id
        JOIN games g ON g.game_id = pgs.game_id
        JOIN seasons s ON s.season_id = g.season_id
        WHERE pgs.player_id = %s
          {team_clause}
          {game_scope_clause}
          {season_clause}
        GROUP BY p.player_name;
        """

    def _player_profile_by_season_sql(
        self,
        team_clause: str,
        game_scope_clause: str,
        season_clause: str,
    ) -> str:
        return f"""
        SELECT
          p.player_name,
          s.season_label,
          COUNT(*) AS games,
          ROUND(AVG(pgs.points)::numeric, 2) AS avg_points,
          ROUND(AVG(pgs.rebounds)::numeric, 2) AS avg_rebounds,
          ROUND(AVG(pgs.assists)::numeric, 2) AS avg_assists,
          ROUND(AVG(pgs.steals)::numeric, 2) AS avg_steals,
          ROUND(AVG(pgs.blocks)::numeric, 2) AS avg_blocks,
          ROUND(AVG(pgs.turnovers)::numeric, 2) AS avg_turnovers,
          ROUND(AVG(pgs.minutes)::numeric, 2) AS avg_minutes,
          ROUND(
            (SUM(COALESCE(pgs.fg_made, 0))::numeric / NULLIF(SUM(COALESCE(pgs.fg_attempts, 0)), 0)) * 100,
            2
          ) AS fg_pct,
          ROUND(
            (SUM(COALESCE(pgs.three_made, 0))::numeric / NULLIF(SUM(COALESCE(pgs.three_attempts, 0)), 0)) * 100,
            2
          ) AS three_pct,
          ROUND(
            (SUM(COALESCE(pgs.ft_made, 0))::numeric / NULLIF(SUM(COALESCE(pgs.ft_attempts, 0)), 0)) * 100,
            2
          ) AS ft_pct
        FROM player_game_stats pgs
        JOIN players p ON p.player_id = pgs.player_id
        JOIN games g ON g.game_id = pgs.game_id
        JOIN seasons s ON s.season_id = g.season_id
        WHERE pgs.player_id = %s
          {team_clause}
          {game_scope_clause}
          {season_clause}
        GROUP BY p.player_name, s.start_year, s.season_label
        ORDER BY s.start_year;
        """

    def _player_stat_sql(
        self,
        metric: str,
        operation: str,
        team_clause: str,
        game_scope_clause: str,
        season_clause: str,
    ) -> str:
        requested_value_expr = self._player_operation_expression(metric, operation)
        return f"""
        SELECT
          p.player_name,
          %s AS metric_name,
          %s AS stat_operation,
          COUNT(*) AS games,
          ROUND(SUM(COALESCE(pgs.{metric}, 0))::numeric, 2) AS total_value,
          ROUND(AVG(pgs.{metric})::numeric, 2) AS avg_value,
          ROUND(MAX(pgs.{metric})::numeric, 2) AS max_value,
          ROUND(MIN(pgs.{metric})::numeric, 2) AS min_value,
          COUNT(pgs.{metric}) AS non_null_games,
          ROUND((SUM(COALESCE(pgs.{metric}, 0))::numeric / NULLIF(COUNT(*), 0))::numeric, 2) AS per_game_value,
          {requested_value_expr} AS requested_value
        FROM player_game_stats pgs
        JOIN players p ON p.player_id = pgs.player_id
        JOIN games g ON g.game_id = pgs.game_id
        JOIN seasons s ON s.season_id = g.season_id
        WHERE pgs.player_id = %s
          {team_clause}
          {game_scope_clause}
          {season_clause}
        GROUP BY p.player_name;
        """

    def _player_stat_by_season_sql(
        self,
        metric: str,
        operation: str,
        team_clause: str,
        game_scope_clause: str,
        season_clause: str,
    ) -> str:
        requested_value_expr = self._player_operation_expression(metric, operation)
        return f"""
        SELECT
          p.player_name,
          s.season_label,
          %s AS metric_name,
          %s AS stat_operation,
          COUNT(*) AS games,
          ROUND(SUM(COALESCE(pgs.{metric}, 0))::numeric, 2) AS total_value,
          ROUND(AVG(pgs.{metric})::numeric, 2) AS avg_value,
          ROUND(MAX(pgs.{metric})::numeric, 2) AS max_value,
          ROUND(MIN(pgs.{metric})::numeric, 2) AS min_value,
          COUNT(pgs.{metric}) AS non_null_games,
          ROUND((SUM(COALESCE(pgs.{metric}, 0))::numeric / NULLIF(COUNT(*), 0))::numeric, 2) AS per_game_value,
          {requested_value_expr} AS requested_value
        FROM player_game_stats pgs
        JOIN players p ON p.player_id = pgs.player_id
        JOIN games g ON g.game_id = pgs.game_id
        JOIN seasons s ON s.season_id = g.season_id
        WHERE pgs.player_id = %s
          {team_clause}
          {game_scope_clause}
          {season_clause}
        GROUP BY p.player_name, s.start_year, s.season_label
        ORDER BY s.start_year;
        """

    def _build_player_single_game_high(self, spec: QuerySpec, context: ResolvedContext) -> SQLPlan | None:
        if not context.players:
            return None

        player = context.players[0]
        metric = self._safe_player_metric(spec.metric)
        game_scope_clause, game_scope_note = self._scope_clause(spec.game_scope)
        season_clause, season_params, season_note = self._season_clause(context)
        params: list[object] = [metric, player.id]

        team_clause = ""
        team_note = "Team scope: all teams."
        if context.teams and spec.against_mode:
            opponent = context.teams[0]
            team_clause = """
            AND (
              (g.home_team_id = pgs.team_id AND g.away_team_id = %s)
              OR (g.away_team_id = pgs.team_id AND g.home_team_id = %s)
            )
            """
            params.extend([opponent.id, opponent.id])
            team_note = f"Opponent scope: {opponent.name}."
        elif context.teams:
            team = context.teams[0]
            team_clause = "AND pgs.team_id = %s"
            params.append(team.id)
            team_note = f"Team scope: {team.name}."

        params.extend(season_params)

        sql = f"""
        SELECT
          p.player_name,
          %s AS metric_name,
          pgs.{metric} AS metric_value,
          g.game_date,
          s.season_label,
          team.team_name,
          opp.team_name AS opponent_team,
          g.game_type
        FROM player_game_stats pgs
        JOIN players p ON p.player_id = pgs.player_id
        JOIN games g ON g.game_id = pgs.game_id
        JOIN seasons s ON s.season_id = g.season_id
        JOIN teams team ON team.team_id = pgs.team_id
        JOIN teams opp ON opp.team_id = CASE
          WHEN g.home_team_id = pgs.team_id THEN g.away_team_id
          ELSE g.home_team_id
        END
        WHERE pgs.player_id = %s
          {team_clause}
          {game_scope_clause}
          {season_clause}
          AND pgs.{metric} IS NOT NULL
        ORDER BY pgs.{metric} DESC, g.game_date DESC
        LIMIT 1;
        """

        return SQLPlan(
            sql=sql,
            params=tuple(params),
            source="query_spec",
            notes=[
                f"Family: {spec.family.value}",
                f"Metric: {metric}",
                team_note,
                game_scope_note,
                season_note,
            ],
        )

    def _build_player_ranking(self, spec: QuerySpec, context: ResolvedContext) -> SQLPlan:
        season_clause, season_params, season_note = self._season_clause(context)
        game_scope_clause, game_scope_note = self._scope_clause(spec.game_scope)
        ranking_limit = max(1, min(spec.ranking_limit, 50))
        metric = self._safe_player_metric(spec.metric)

        metric_map = {
            "points": ("avg_points", "AVG(pgs.points)"),
            "assists": ("avg_assists", "AVG(pgs.assists)"),
            "rebounds": ("avg_rebounds", "AVG(pgs.rebounds)"),
            "steals": ("avg_steals", "AVG(pgs.steals)"),
            "blocks": ("avg_blocks", "AVG(pgs.blocks)"),
            "turnovers": ("avg_turnovers", "AVG(pgs.turnovers)"),
            "minutes": ("avg_minutes", "AVG(pgs.minutes)"),
        }
        order_alias, order_expr = metric_map.get(metric, metric_map["points"])

        sql = f"""
        SELECT
          p.player_name,
          COUNT(*) AS games,
          ROUND(AVG(pgs.points)::numeric, 2) AS avg_points,
          ROUND(AVG(pgs.assists)::numeric, 2) AS avg_assists,
          ROUND(AVG(pgs.rebounds)::numeric, 2) AS avg_rebounds,
          ROUND(AVG(pgs.turnovers)::numeric, 2) AS avg_turnovers,
          ROUND(AVG(pgs.minutes)::numeric, 2) AS avg_minutes,
          ROUND(({order_expr})::numeric, 2) AS metric_value
        FROM player_game_stats pgs
        JOIN players p ON p.player_id = pgs.player_id
        JOIN games g ON g.game_id = pgs.game_id
        JOIN seasons s ON s.season_id = g.season_id
        WHERE pgs.minutes IS NOT NULL
          {game_scope_clause}
          {season_clause}
        GROUP BY p.player_name
        HAVING COUNT(*) >= 20
        ORDER BY {order_alias} DESC
        LIMIT {ranking_limit};
        """

        return SQLPlan(
            sql=sql,
            params=tuple(season_params),
            source="query_spec",
            notes=[
                f"Family: {spec.family.value}",
                f"Metric: {metric}",
                game_scope_note,
                season_note,
                f"Ranking limit: top {ranking_limit}",
            ],
        )

    def _build_team_comparison(self, spec: QuerySpec, context: ResolvedContext) -> SQLPlan | None:
        if len(context.teams) < 2:
            return None

        team_a = context.teams[0]
        team_b = context.teams[1]
        game_scope_clause, game_scope_note = self._scope_clause(spec.game_scope)
        season_clause, season_params, season_note = self._season_clause(context)

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
          {season_clause}
        GROUP BY s.start_year, s.season_label, t.team_name
        ORDER BY s.start_year, t.team_name;
        """

        return SQLPlan(
            sql=sql,
            params=(team_a.id, team_b.id, *season_params),
            source="query_spec",
            notes=[
                f"Family: {spec.family.value}",
                f"Comparing {team_a.name} vs {team_b.name}",
                game_scope_note,
                season_note,
            ],
        )

    def _build_team_trend(self, spec: QuerySpec, context: ResolvedContext) -> SQLPlan | None:
        if not context.teams:
            return None

        team = context.teams[0]
        game_scope_clause, game_scope_note = self._scope_clause(spec.game_scope)
        season_clause, season_params, season_note = self._season_clause(context)

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
          {season_clause}
        GROUP BY s.start_year, s.season_label
        ORDER BY s.start_year;
        """

        return SQLPlan(
            sql=sql,
            params=(team.id, *season_params),
            source="query_spec",
            notes=[
                f"Family: {spec.family.value}",
                f"Trend for {team.name}",
                game_scope_note,
                season_note,
            ],
        )

    def _build_team_stat(self, spec: QuerySpec, context: ResolvedContext) -> SQLPlan | None:
        if not context.teams:
            return None

        team = context.teams[0]
        game_scope_clause, game_scope_note = self._scope_clause(spec.game_scope)
        season_clause, season_params, season_note = self._season_clause(context)

        sql = f"""
        SELECT
          t.team_name,
          COUNT(*) AS games,
          SUM(CASE WHEN tgr.is_win = 1 THEN 1 ELSE 0 END) AS wins,
          SUM(CASE WHEN tgr.is_win = 0 THEN 1 ELSE 0 END) AS losses,
          ROUND(AVG(tgr.is_win::numeric) * 100, 2) AS win_pct,
          ROUND(AVG(tgr.team_points)::numeric, 2) AS avg_points,
          ROUND(AVG(tgr.opponent_points)::numeric, 2) AS avg_points_allowed
        FROM team_game_results tgr
        JOIN games g ON g.game_id = tgr.game_id
        JOIN seasons s ON s.season_id = g.season_id
        JOIN teams t ON t.team_id = tgr.team_id
        WHERE tgr.team_id = %s
          {game_scope_clause}
          {season_clause}
        GROUP BY t.team_name;
        """

        return SQLPlan(
            sql=sql,
            params=(team.id, *season_params),
            source="query_spec",
            notes=[
                f"Family: {spec.family.value}",
                f"Team stat query for {team.name}",
                game_scope_note,
                season_note,
            ],
        )

    def _build_team_head_to_head(self, spec: QuerySpec, context: ResolvedContext) -> SQLPlan | None:
        if len(context.teams) < 2:
            return None

        team_a = context.teams[0]
        team_b = context.teams[1]
        game_scope_clause, game_scope_note = self._scope_clause(spec.game_scope)
        season_clause, season_params, season_note = self._season_clause(context)
        params: list[object] = [
            team_a.id,
            team_b.id,
            team_a.id,
            team_a.id,
            team_b.id,
            team_a.id,
            team_b.id,
            team_b.id,
            team_a.id,
        ]
        params.extend(season_params)

        sql = f"""
        SELECT
          ta.team_name AS team_a,
          tb.team_name AS team_b,
          COUNT(*) AS games,
          SUM(CASE WHEN g.winner_team_id = %s THEN 1 ELSE 0 END) AS team_a_wins,
          SUM(CASE WHEN g.winner_team_id = %s THEN 1 ELSE 0 END) AS team_b_wins,
          ROUND(AVG(CASE WHEN g.winner_team_id = %s THEN 1 ELSE 0 END)::numeric * 100, 2)
            AS team_a_win_pct
        FROM games g
        JOIN teams ta ON ta.team_id = %s
        JOIN teams tb ON tb.team_id = %s
        WHERE (
            (g.home_team_id = %s AND g.away_team_id = %s)
            OR (g.home_team_id = %s AND g.away_team_id = %s)
          )
          {game_scope_clause}
          {season_clause}
        GROUP BY ta.team_name, tb.team_name;
        """

        return SQLPlan(
            sql=sql,
            params=tuple(params),
            source="query_spec",
            notes=[
                f"Family: {spec.family.value}",
                f"Head-to-head: {team_a.name} vs {team_b.name}",
                game_scope_note,
                season_note,
            ],
        )

    def _build_team_ranking(self, spec: QuerySpec, context: ResolvedContext) -> SQLPlan:
        game_scope_clause, game_scope_note = self._scope_clause(spec.game_scope)
        season_clause, season_params, season_note = self._season_clause(context)
        metric_alias, metric_expr, metric_direction = self._team_ranking_metric(spec.metric)
        ranking_limit = max(1, min(spec.ranking_limit, 50))

        sql = f"""
        SELECT
          t.team_name,
          COUNT(*) AS games,
          SUM(CASE WHEN tgr.is_win = 1 THEN 1 ELSE 0 END) AS wins,
          ROUND(AVG(tgr.is_win::numeric) * 100, 2) AS win_pct,
          ROUND(AVG(tgr.team_points)::numeric, 2) AS avg_points,
          ROUND(AVG(tgr.opponent_points)::numeric, 2) AS avg_points_allowed,
          {metric_expr} AS metric_value
        FROM team_game_results tgr
        JOIN teams t ON t.team_id = tgr.team_id
        JOIN games g ON g.game_id = tgr.game_id
        JOIN seasons s ON s.season_id = g.season_id
        WHERE 1=1
          {game_scope_clause}
          {season_clause}
        GROUP BY t.team_name
        HAVING COUNT(*) >= 20
        ORDER BY metric_value {metric_direction}
        LIMIT {ranking_limit};
        """

        return SQLPlan(
            sql=sql,
            params=tuple(season_params),
            source="query_spec",
            notes=[
                f"Family: {spec.family.value}",
                f"Metric: {metric_alias}",
                game_scope_note,
                season_note,
                f"Ranking limit: top {ranking_limit}",
            ],
        )

    def _scope_clause(self, game_scope: str) -> tuple[str, str]:
        if game_scope == "all":
            return "AND 1=1", "Game scope: all games."
        if game_scope == "playoffs":
            return "AND g.game_type = 'playoffs'", "Game scope: playoffs."
        if game_scope == "preseason":
            return "AND g.game_type = 'preseason'", "Game scope: preseason."
        return "AND g.game_type = 'regular'", "Game scope: regular season (default)."

    def _season_clause(self, context: ResolvedContext) -> tuple[str, tuple[object, ...], str]:
        if not context.seasons:
            return "", (), "Season scope: all available seasons."
        if len(context.seasons) == 1:
            season = context.seasons[0]
            return "AND s.season_label = %s", (season,), f"Season scope: {season}."
        placeholders = ", ".join(["%s"] * len(context.seasons))
        return (
            f"AND s.season_label IN ({placeholders})",
            tuple(context.seasons),
            f"Season scope: {context.seasons[0]} to {context.seasons[-1]} ({len(context.seasons)} seasons).",
        )

    def _safe_player_metric(self, metric: str) -> str:
        allowed = {"points", "assists", "rebounds", "steals", "blocks", "turnovers", "minutes"}
        return metric if metric in allowed else "points"

    def _safe_stat_operation(self, operation: str) -> str:
        allowed = {"sum", "avg", "max", "min", "count"}
        return operation if operation in allowed else "avg"

    def _player_operation_expression(self, metric: str, operation: str) -> str:
        if operation == "sum":
            return f"ROUND(SUM(COALESCE(pgs.{metric}, 0))::numeric, 2)"
        if operation == "max":
            return f"ROUND(MAX(pgs.{metric})::numeric, 2)"
        if operation == "min":
            return f"ROUND(MIN(pgs.{metric})::numeric, 2)"
        if operation == "count":
            return f"COUNT(pgs.{metric})"
        return f"ROUND(AVG(pgs.{metric})::numeric, 2)"

    def _team_ranking_metric(self, metric: str) -> tuple[str, str, str]:
        metric_map = {
            "win_pct": ("win_pct", "ROUND(AVG(tgr.is_win::numeric) * 100, 2)", "DESC"),
            "wins": ("wins", "SUM(CASE WHEN tgr.is_win = 1 THEN 1 ELSE 0 END)", "DESC"),
            "points": ("avg_points", "ROUND(AVG(tgr.team_points)::numeric, 2)", "DESC"),
            "opponent_points": ("avg_points_allowed", "ROUND(AVG(tgr.opponent_points)::numeric, 2)", "ASC"),
        }
        return metric_map.get(metric, metric_map["win_pct"])
