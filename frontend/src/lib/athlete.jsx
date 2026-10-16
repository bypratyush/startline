import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api.js";

// The athlete profile lives in the database; the browser only remembers its id.
const KEY = "startline.athlete";

function readId() {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

function writeId(id) {
  try {
    if (id) localStorage.setItem(KEY, id);
    else localStorage.removeItem(KEY);
  } catch {
    /* storage blocked: the profile still works for this tab */
  }
}

const AthleteContext = createContext(null);

export function AthleteProvider({ children }) {
  const [id, setId] = useState(readId);
  const [athlete, setAthlete] = useState(null);
  const [loading, setLoading] = useState(Boolean(readId()));
  const [catalog, setCatalog] = useState({ sports: [], cities: [], loaded: false });
  const [saved, setSaved] = useState(() => new Set());

  useEffect(() => {
    Promise.all([api.get("/api/sports"), api.get("/api/cities")])
      .then(([sports, cities]) => setCatalog({ sports, cities, loaded: true }))
      .catch(() => setCatalog((c) => ({ ...c, loaded: true, failed: true })));
  }, []);

  useEffect(() => {
    if (!id) {
      setAthlete(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    api
      .get(`/api/athletes/${id}`)
      .then(setAthlete)
      .catch((e) => {
        if (e.status === 404) {
          writeId(null);
          setId(null);
        }
      })
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id) {
      setSaved(new Set());
      return;
    }
    api
      .get(`/api/athletes/${id}/saved`)
      .then((rows) => setSaved(new Set(rows.map((r) => r.slug))))
      .catch(() => {});
  }, [id]);

  const toggleSaved = useCallback(
    async (slug) => {
      if (!id) return false;
      const isSaved = saved.has(slug);
      setSaved((prev) => {
        const next = new Set(prev);
        if (isSaved) next.delete(slug);
        else next.add(slug);
        return next;
      });
      try {
        if (isSaved) await api.del(`/api/athletes/${id}/saved/${slug}`);
        else await api.post(`/api/athletes/${id}/saved`, { event: slug });
      } catch {
        setSaved((prev) => {
          const next = new Set(prev);
          if (isSaved) next.add(slug);
          else next.delete(slug);
          return next;
        });
      }
      return !isSaved;
    },
    [id, saved],
  );

  const save = useCallback(
    async (body) => {
      const saved = id ? await api.put(`/api/athletes/${id}`, body) : await api.post("/api/athletes", body);
      writeId(saved.id);
      setId(saved.id);
      setAthlete(saved);
      return saved;
    },
    [id],
  );

  const patch = useCallback(
    async (body) => {
      if (!id) return null;
      const saved = await api.patch(`/api/athletes/${id}`, body);
      setAthlete(saved);
      return saved;
    },
    [id],
  );

  const signOut = useCallback(() => {
    writeId(null);
    setId(null);
    setAthlete(null);
  }, []);

  const value = useMemo(
    () => ({
      id,
      athlete,
      loading,
      save,
      patch,
      signOut,
      saved,
      toggleSaved,
      sports: catalog.sports,
      cities: catalog.cities,
      catalogLoaded: catalog.loaded,
      catalogFailed: catalog.failed,
      sportBySlug: Object.fromEntries(catalog.sports.map((s) => [s.slug, s])),
    }),
    [id, athlete, loading, save, patch, signOut, saved, toggleSaved, catalog],
  );

  return <AthleteContext.Provider value={value}>{children}</AthleteContext.Provider>;
}

export function useAthlete() {
  return useContext(AthleteContext);
}

// Small per-browser preferences (last city browsed without a profile, checklist ticks)
export function usePersisted(key, initial) {
  const [value, setValue] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? initial : JSON.parse(raw);
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* ignore */
    }
  }, [key, value]);
  return [value, setValue];
}
