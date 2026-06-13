import { Router, type IRouter } from "express";
import { eq, sql, desc } from "drizzle-orm";
import { db, initiativesTable, initiativeUpdatesTable } from "@workspace/db";
import {
  GetRecentActivityQueryParams,
  GetDashboardSummaryResponse,
  GetRecentActivityResponse,
} from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/dashboard/summary", async (_req, res): Promise<void> => {
  const rows = await db.select().from(initiativesTable);

  const total = rows.length;
  const onTrack = rows.filter((r) => r.status === "on_track").length;
  const atRisk = rows.filter((r) => r.status === "at_risk").length;
  const delayed = rows.filter((r) => r.status === "delayed").length;
  const completed = rows.filter((r) => r.status === "completed").length;
  const notStarted = rows.filter((r) => r.status === "not_started").length;
  const avgProgress = total > 0 ? rows.reduce((sum, r) => sum + r.progress, 0) / total : 0;

  const deptMap = new Map<string, number>();
  for (const row of rows) {
    if (row.department) {
      deptMap.set(row.department, (deptMap.get(row.department) ?? 0) + 1);
    }
  }
  const byDepartment = Array.from(deptMap.entries()).map(([department, count]) => ({ department, count }));

  const priorityMap = new Map<string, number>();
  for (const row of rows) {
    priorityMap.set(row.priority, (priorityMap.get(row.priority) ?? 0) + 1);
  }
  const byPriority = Array.from(priorityMap.entries()).map(([priority, count]) => ({ priority, count }));

  res.json(
    GetDashboardSummaryResponse.parse({
      total,
      onTrack,
      atRisk,
      delayed,
      completed,
      notStarted,
      avgProgress,
      byDepartment,
      byPriority,
    }),
  );
});

router.get("/dashboard/recent-activity", async (req, res): Promise<void> => {
  const params = GetRecentActivityQueryParams.safeParse(req.query);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const limit = params.data.limit ?? 10;

  const rows = await db
    .select({
      id: initiativeUpdatesTable.id,
      initiativeId: initiativeUpdatesTable.initiativeId,
      initiativeTitle: initiativesTable.title,
      note: initiativeUpdatesTable.note,
      author: initiativeUpdatesTable.author,
      createdAt: initiativeUpdatesTable.createdAt,
    })
    .from(initiativeUpdatesTable)
    .innerJoin(initiativesTable, eq(initiativeUpdatesTable.initiativeId, initiativesTable.id))
    .orderBy(desc(initiativeUpdatesTable.createdAt))
    .limit(limit);

  res.json(
    GetRecentActivityResponse.parse(
      rows.map((r) => ({
        id: r.id,
        initiativeId: r.initiativeId,
        initiativeTitle: r.initiativeTitle,
        note: r.note,
        author: r.author,
        createdAt: r.createdAt.toISOString(),
      })),
    ),
  );
});

export default router;
