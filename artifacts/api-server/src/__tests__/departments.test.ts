import { describe, it, expect, beforeEach, vi } from "vitest";
import request from "supertest";
import app from "../app.js";
import { makeChain } from "./helpers.js";

const mockDb = vi.hoisted(() => ({
  select: vi.fn(),
  insert: vi.fn(),
  update: vi.fn(),
  delete: vi.fn(),
}));

vi.mock("@workspace/db", () => ({
  db: mockDb,
  initiativesTable: {},
  initiativeUpdatesTable: {},
  departmentsTable: {},
}));

beforeEach(() => {
  vi.clearAllMocks();
});

const fakeDept = { id: 1, name: "Engineering" };

describe("GET /api/departments", () => {
  it("returns 200 with a list of departments", async () => {
    mockDb.select.mockReturnValue(makeChain([fakeDept]));
    const res = await request(app).get("/api/departments");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].name).toBe("Engineering");
  });

  it("returns an empty array when no departments exist", async () => {
    mockDb.select.mockReturnValue(makeChain([]));
    const res = await request(app).get("/api/departments");
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });
});

describe("POST /api/departments", () => {
  it("returns 201 with the created department", async () => {
    mockDb.insert.mockReturnValue(makeChain([fakeDept]));
    const res = await request(app)
      .post("/api/departments")
      .send({ name: "Engineering" });
    expect(res.status).toBe(201);
    expect(res.body.name).toBe("Engineering");
  });

  it("returns 400 when name is missing", async () => {
    const res = await request(app).post("/api/departments").send({});
    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty("error");
  });
});
