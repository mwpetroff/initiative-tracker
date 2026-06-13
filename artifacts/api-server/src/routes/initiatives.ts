import { Router, type IRouter } from "express";
import { eq, and, sql } from "drizzle-orm";
import { db, initiativesTable, initiativeUpdatesTable } from "@workspace/db";
import {
  ListInitiativesQueryParams,
  ListInitiativesResponse,
  CreateInitiativeBody,
  GetInitiativeParams,
  GetInitiativeResponse,
  UpdateInitiativeParams,
  UpdateInitiativeBody,
  UpdateInitiativeResponse,
  DeleteInitiativeParams,
  ListInitiativeUpdatesParams,
  ListInitiativeUpdatesResponse,
  CreateInitiativeUpdateParams,
  CreateInitiativeUpdateBody,
} from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/initiatives", async (req, res): Promise<void> => {
  const params = ListInitiativesQueryParams.safeParse(req.query);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const conditions = [];
  if (params.data.status) conditions.push(eq(initiativesTable.status, params.data.status));
  if (params.data.department) conditions.push(eq(initiativesTable.department, params.data.department));
  if (params.data.priority) conditions.push(eq(initiativesTable.priority, params.data.priority));

  const rows = await db
    .select()
    .from(initiativesTable)
    .where(conditions.length > 0 ? and(...conditions) : undefined)
    .orderBy(initiativesTable.createdAt);

  res.json(ListInitiativesResponse.parse(rows.map(toDto)));
});

router.post("/initiatives", async (req, res): Promise<void> => {
  const parsed = CreateInitiativeBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const [row] = await db.insert(initiativesTable).values(parsed.data).returning();
  res.status(201).json(GetInitiativeResponse.parse(toDto(row)));
});

router.get("/initiatives/:id", async (req, res): Promise<void> => {
  const params = GetInitiativeParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [row] = await db.select().from(initiativesTable).where(eq(initiativesTable.id, params.data.id));
  if (!row) {
    res.status(404).json({ error: "Initiative not found" });
    return;
  }

  res.json(GetInitiativeResponse.parse(toDto(row)));
});

router.patch("/initiatives/:id", async (req, res): Promise<void> => {
  const params = UpdateInitiativeParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const parsed = UpdateInitiativeBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const [row] = await db
    .update(initiativesTable)
    .set(parsed.data)
    .where(eq(initiativesTable.id, params.data.id))
    .returning();

  if (!row) {
    res.status(404).json({ error: "Initiative not found" });
    return;
  }

  res.json(UpdateInitiativeResponse.parse(toDto(row)));
});

router.delete("/initiatives/:id", async (req, res): Promise<void> => {
  const params = DeleteInitiativeParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [row] = await db
    .delete(initiativesTable)
    .where(eq(initiativesTable.id, params.data.id))
    .returning();

  if (!row) {
    res.status(404).json({ error: "Initiative not found" });
    return;
  }

  res.sendStatus(204);
});

router.get("/initiatives/:id/updates", async (req, res): Promise<void> => {
  const params = ListInitiativeUpdatesParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const rows = await db
    .select()
    .from(initiativeUpdatesTable)
    .where(eq(initiativeUpdatesTable.initiativeId, params.data.id))
    .orderBy(initiativeUpdatesTable.createdAt);

  res.json(ListInitiativeUpdatesResponse.parse(rows.map(updateToDto)));
});

router.post("/initiatives/:id/updates", async (req, res): Promise<void> => {
  const params = CreateInitiativeUpdateParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const parsed = CreateInitiativeUpdateBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const [row] = await db
    .insert(initiativeUpdatesTable)
    .values({ initiativeId: params.data.id, ...parsed.data })
    .returning();

  res.status(201).json(updateToDto(row));
});

function toDto(row: typeof initiativesTable.$inferSelect) {
  return {
    id: row.id,
    title: row.title,
    description: row.description ?? null,
    status: row.status,
    progress: row.progress,
    priority: row.priority,
    owner: row.owner ?? null,
    department: row.department ?? null,
    startDate: row.startDate ?? null,
    endDate: row.endDate ?? null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function updateToDto(row: typeof initiativeUpdatesTable.$inferSelect) {
  return {
    id: row.id,
    initiativeId: row.initiativeId,
    note: row.note,
    author: row.author,
    createdAt: row.createdAt.toISOString(),
  };
}

export default router;
