#include "postgres.h"

#include "fmgr.h"
#include "nodes/parsenodes.h"
#include "nodes/plannodes.h"
#include "tcop/tcopprot.h"
#include "utils/builtins.h"

PG_MODULE_MAGIC;

PG_FUNCTION_INFO_V1(ce_native_plan_rows);

/*
 * Return the backend's unrounded top-level Plan.plan_rows for one SELECT.
 * This is deliberately a validation oracle, not an optimizer hot-path API.
 */
Datum
ce_native_plan_rows(PG_FUNCTION_ARGS)
{
	char       *query_string = text_to_cstring(PG_GETARG_TEXT_PP(0));
	List       *raw_parsetree_list;
	RawStmt    *rawstmt;
	List       *querytree_list;
	List       *plantree_list;
	PlannedStmt *pstmt;

	raw_parsetree_list = pg_parse_query(query_string);
	if (list_length(raw_parsetree_list) != 1)
		ereport(ERROR,
				(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
				 errmsg("exactly one statement is required")));

	rawstmt = linitial_node(RawStmt, raw_parsetree_list);
	querytree_list = pg_analyze_and_rewrite_fixedparams(rawstmt, query_string,
													 NULL, 0, NULL);
	plantree_list = pg_plan_queries(querytree_list, query_string, 0, NULL);
	if (list_length(plantree_list) != 1)
		ereport(ERROR,
				(errcode(ERRCODE_FEATURE_NOT_SUPPORTED),
				 errmsg("statement did not produce exactly one plan")));

	pstmt = linitial_node(PlannedStmt, plantree_list);
	if (pstmt->commandType != CMD_SELECT || pstmt->planTree == NULL)
		ereport(ERROR,
				(errcode(ERRCODE_FEATURE_NOT_SUPPORTED),
				 errmsg("only SELECT statements are supported")));

	PG_RETURN_FLOAT8(pstmt->planTree->plan_rows);
}
