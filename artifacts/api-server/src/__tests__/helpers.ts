export function makeChain(resolveWith: unknown): any {
  const chain: any = new Proxy(
    {},
    {
      get(_target, prop) {
        if (prop === "then") {
          return (
            resolve: (v: unknown) => unknown,
            reject?: (e: unknown) => unknown,
          ) => Promise.resolve(resolveWith).then(resolve, reject);
        }
        if (prop === "catch") {
          return (reject: (e: unknown) => unknown) =>
            Promise.resolve(resolveWith).catch(reject);
        }
        if (prop === "finally") {
          return (onFinally: () => void) =>
            Promise.resolve(resolveWith).finally(onFinally);
        }
        return () => chain;
      },
    },
  );
  return chain;
}

export const fakeInitiative = {
  id: 1,
  title: "Test Initiative",
  description: null,
  status: "on_track" as const,
  progress: 50,
  priority: "medium" as const,
  owner: null,
  department: null,
  startDate: null,
  endDate: null,
  createdAt: new Date("2024-01-15T10:00:00Z"),
  updatedAt: new Date("2024-01-20T12:00:00Z"),
};

export const fakeUpdate = {
  id: 10,
  initiativeId: 1,
  note: "Making good progress",
  author: "Jane Smith",
  createdAt: new Date("2024-01-18T09:00:00Z"),
};
