import { describe, it, expect, beforeEach, vi } from "vitest";
import request from "supertest";
import app from "../app.js";
import { makeChain, fakeInitiative } from "./helpers.js";

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

describe("GET /api/dashboard/summary", () => {
  it("returns 200 with aggregated stats for multiple initiatives", async () => {
    const rows = [
      { ...fakeInitiative, id: 1, status: "on_track", progress: 60, department: "Engineering" },
      { ...fakeInitiative, id: 2, status: "at_risk", progress: 30, department: "Engineering" },
      { ...fakeInitiative, id: 3, status: "delayed", progress: 10, department: "Marketing" },
      { ...fakeInitiative, id: 4, status: "completed", progress: 100, department: null },
      { ...fakeInitiative, id: 5, status: "not_started", progress: 0, department: "Marketing" },
    ];
    mockDb.select.mockReturnValue(makeChain(rows));

    const res = await request(app).get("/api/dashboard/summary");

    expect(res.status).toBe(200);
    expect(res.body.total).toBe(5);
    expect(res.body.onTrack).toBe(1);
    expect(res.body.atRisk).toBe(1);
    expect(res.body.delayed).toBe(1);
    expect(res.body.completed).toBe(1);
    expect(res.body.notStarted).toBe(1);
    expect(res.body.avgProgress).toBe(40);
  });

  it("returns zero stats when no initiatives exist", async () => {
    mockDb.select.mockReturnValue(makeChain([]));
    const res = await request(app).get("/api/dashboard/summary");
    expect(res.status).toBe(200);
    expect(res.body.total).toBe(0);
    expect(res.body.avgProgress).toBe(0);
    expect(res.body.byDepartment).toEqual([]);
    expect(res.body.byPriority).toEqual([]);
  });

  it("groups initiatives by department correctly", async () => {
    const rows = [
      { ...fakeInitiative, id: 1, department: "Engineering" },
      { ...fakeInitiative, id: 2, department: "Engineering" },
      { ...fakeInitiative, id: 3, department: "Marketing" },
    ];
    mockDb.select.mockReturnValue(makeChain(rows));
    const res = await request(app).get("/api/dashboard/summary");
    expect(res.status).toBe(200);
    const deptMap = Object.fromEntries(
      res.body.byDepartment.map((d: { department: string; count: number }) => [
        d.department,
        d.count,
      ]),
    );
    expect(deptMap["Engineering"]).toBe(2);
    expect(deptMap["Marketing"]).toBe(1);
  });

  it("excludes initiatives with no department from byDepartment", async () => {
    const rows = [
      { ...fakeInitiative, id: 1, department: null },
      { ...fakeInitiative, id: 2, department: "Engineering" },
    ];
    mockDb.select.mockReturnValue(makeChain(rows));
    const res = await request(app).get("/api/dashboard/summary");
    expect(res.body.byDepartment).toHaveLength(1);
    expect(res.body.byDepartment[0].department).toBe("Engineering");
  });
});

describe("GET /api/dashboard/recent-activity", () => {
  const fakeActivity = {
    id: 1,
    initiativeId: 1,
    initiativeTitle: "Test Initiative",
    note: "All systems go",
    author: "Alice",
    createdAt: new Date("2024-01-18T09:00:00Z"),
  };

  it("returns 200 with recent activity items", async () => {
    mockDb.select.mockReturnValue(makeChain([fakeActivity]));
    const res = await request(app).get("/api/dashboard/recent-activity");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].note).toBe("All systems go");
    expect(res.body[0].initiativeTitle).toBe("Test Initiative");
  });

  it("returns 200 with an empty array when no activity exists", async () => {
    mockDb.select.mockReturnValue(makeChain([]));
    const res = await request(app).get("/api/dashboard/recent-activity");
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it("accepts a custom limit query param", async () => {
    mockDb.select.mockReturnValue(makeChain([fakeActivity]));
    const res = await request(app)
      .get("/api/dashboard/recent-activity")
      .query({ limit: 5 });
    expect(res.status).toBe(200);
  });

  it("returns 400 for an invalid limit value", async () => {
    const res = await request(app)
      .get("/api/dashboard/recent-activity")
      .query({ limit: "not-a-number" });
    expect(res.status).toBe(400);
  });
});
