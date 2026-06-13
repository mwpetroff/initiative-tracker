import { describe, it, expect, beforeEach, vi } from "vitest";
import request from "supertest";
import app from "../app.js";
import { makeChain, fakeInitiative, fakeUpdate } from "./helpers.js";

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

describe("GET /api/initiatives", () => {
  it("returns 200 with an array of initiatives", async () => {
    mockDb.select.mockReturnValue(makeChain([fakeInitiative]));
    const res = await request(app).get("/api/initiatives");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].id).toBe(1);
    expect(res.body[0].title).toBe("Test Initiative");
    expect(res.body[0].status).toBe("on_track");
  });

  it("returns 200 with an empty array when no initiatives exist", async () => {
    mockDb.select.mockReturnValue(makeChain([]));
    const res = await request(app).get("/api/initiatives");
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it("returns 200 with empty results for an unrecognized status filter", async () => {
    mockDb.select.mockReturnValue(makeChain([]));
    const res = await request(app)
      .get("/api/initiatives")
      .query({ status: "invalid_status" });
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it("passes a valid status filter through", async () => {
    mockDb.select.mockReturnValue(makeChain([fakeInitiative]));
    const res = await request(app)
      .get("/api/initiatives")
      .query({ status: "on_track" });
    expect(res.status).toBe(200);
    expect(mockDb.select).toHaveBeenCalledOnce();
  });
});

describe("POST /api/initiatives", () => {
  it("returns 201 with the created initiative", async () => {
    mockDb.insert.mockReturnValue(makeChain([fakeInitiative]));
    const res = await request(app).post("/api/initiatives").send({
      title: "Test Initiative",
      status: "on_track",
      progress: 50,
      priority: "medium",
    });
    expect(res.status).toBe(201);
    expect(res.body.id).toBe(1);
    expect(res.body.title).toBe("Test Initiative");
  });

  it("returns 400 when title is missing", async () => {
    const res = await request(app)
      .post("/api/initiatives")
      .send({ status: "on_track" });
    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty("error");
  });

  it("returns 400 when status is invalid", async () => {
    const res = await request(app)
      .post("/api/initiatives")
      .send({ title: "Test", status: "BAD_STATUS" });
    expect(res.status).toBe(400);
  });

  it("returns 400 when progress is out of range", async () => {
    const res = await request(app)
      .post("/api/initiatives")
      .send({ title: "Test", progress: 150 });
    expect(res.status).toBe(400);
  });
});

describe("GET /api/initiatives/:id", () => {
  it("returns 200 with the initiative when found", async () => {
    mockDb.select.mockReturnValue(makeChain([fakeInitiative]));
    const res = await request(app).get("/api/initiatives/1");
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(1);
  });

  it("returns 404 when initiative does not exist", async () => {
    mockDb.select.mockReturnValue(makeChain([]));
    const res = await request(app).get("/api/initiatives/999");
    expect(res.status).toBe(404);
    expect(res.body).toEqual({ error: "Initiative not found" });
  });

  it("returns 400 for a non-numeric id", async () => {
    const res = await request(app).get("/api/initiatives/not-a-number");
    expect(res.status).toBe(400);
  });
});

describe("PATCH /api/initiatives/:id", () => {
  it("returns 200 with the updated initiative", async () => {
    const updated = { ...fakeInitiative, progress: 75 };
    mockDb.update.mockReturnValue(makeChain([updated]));
    const res = await request(app)
      .patch("/api/initiatives/1")
      .send({ progress: 75 });
    expect(res.status).toBe(200);
    expect(res.body.progress).toBe(75);
  });

  it("returns 404 when initiative does not exist", async () => {
    mockDb.update.mockReturnValue(makeChain([]));
    const res = await request(app)
      .patch("/api/initiatives/999")
      .send({ progress: 75 });
    expect(res.status).toBe(404);
  });

  it("returns 400 for an invalid status value", async () => {
    const res = await request(app)
      .patch("/api/initiatives/1")
      .send({ status: "INVALID" });
    expect(res.status).toBe(400);
  });
});

describe("DELETE /api/initiatives/:id", () => {
  it("returns 204 when the initiative is deleted", async () => {
    mockDb.delete.mockReturnValue(makeChain([fakeInitiative]));
    const res = await request(app).delete("/api/initiatives/1");
    expect(res.status).toBe(204);
  });

  it("returns 404 when initiative does not exist", async () => {
    mockDb.delete.mockReturnValue(makeChain([]));
    const res = await request(app).delete("/api/initiatives/999");
    expect(res.status).toBe(404);
  });
});

describe("GET /api/initiatives/:id/updates", () => {
  it("returns 200 with a list of updates", async () => {
    mockDb.select.mockReturnValue(makeChain([fakeUpdate]));
    const res = await request(app).get("/api/initiatives/1/updates");
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].note).toBe("Making good progress");
  });

  it("returns an empty array when there are no updates", async () => {
    mockDb.select.mockReturnValue(makeChain([]));
    const res = await request(app).get("/api/initiatives/1/updates");
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });
});

describe("POST /api/initiatives/:id/updates", () => {
  it("returns 201 with the created update", async () => {
    mockDb.insert.mockReturnValue(makeChain([fakeUpdate]));
    const res = await request(app)
      .post("/api/initiatives/1/updates")
      .send({ note: "Making good progress", author: "Jane Smith" });
    expect(res.status).toBe(201);
    expect(res.body.note).toBe("Making good progress");
    expect(res.body.author).toBe("Jane Smith");
  });

  it("returns 400 when note is missing", async () => {
    const res = await request(app)
      .post("/api/initiatives/1/updates")
      .send({ author: "Jane Smith" });
    expect(res.status).toBe(400);
  });

  it("returns 400 when author is missing", async () => {
    const res = await request(app)
      .post("/api/initiatives/1/updates")
      .send({ note: "Some note" });
    expect(res.status).toBe(400);
  });
});
