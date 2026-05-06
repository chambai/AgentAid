const BASE = "/api";
async function getJson(path) {
    const res = await fetch(`${BASE}${path}`);
    if (!res.ok)
        throw new Error(`${res.status} ${res.statusText} for ${path}`);
    return res.json();
}
export const api = {
    listRuns: (params = {}) => {
        const q = new URLSearchParams();
        if (params.limit !== undefined)
            q.set("limit", String(params.limit));
        if (params.offset !== undefined)
            q.set("offset", String(params.offset));
        const qs = q.toString();
        return getJson(`/runs${qs ? `?${qs}` : ""}`);
    },
    getRun: (id) => getJson(`/runs/${id}`),
    driftState: () => getJson(`/drift`),
};
