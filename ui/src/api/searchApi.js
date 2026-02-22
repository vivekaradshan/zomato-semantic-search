import axios from "axios";

const BASE_URL = "http://localhost:8000";

export const search = async (query, mode, topK = 10) => {
  const endpoint = {
    semantic: "/search/semantic",
    keyword:  "/search/keyword",
    hybrid:   "/search/hybrid",
  }[mode];

  const { data } = await axios.post(`${BASE_URL}${endpoint}`, {
    query,
    top_k: topK,
  });

  return data;
};

// For comparison view — fires both simultaneously
export const compareSearch = async (query, topK = 10) => {
  const [semantic, keyword] = await Promise.all([
    search(query, "semantic", topK),
    search(query, "keyword",  topK),
  ]);
  return { semantic, keyword };
};
