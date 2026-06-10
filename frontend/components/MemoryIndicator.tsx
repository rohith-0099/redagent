import type { AttackCategory } from "@/lib/api";

export interface MemoryRecall {
  category: AttackCategory;
  count: number;
}

// Surfaces the per-target learning moat: when attack-memory (RAG #2) recalls
// prior breaches, RedAgent evolves them instead of starting cold.
export function MemoryIndicator({ recalls }: { recalls: MemoryRecall[] }) {
  if (!recalls.length) return null;
  const total = recalls.reduce((s, r) => s + r.count, 0);

  return (
    <section className="reveal border border-accent/30 bg-base2/60">
      <div className="flex items-center gap-2 border-b border-accent/20 px-3.5 py-2">
        <span className="size-2 bg-accent led-live" aria-hidden />
        <h2 className="text-[11px] font-600 tracking-[0.16em] text-accent">
          ATTACK MEMORY · ADAPTIVE
        </h2>
      </div>
      <div className="flex flex-col gap-2 p-3.5">
        <p className="text-[12px] leading-relaxed text-dim">
          RedAgent recalled{" "}
          <span className="font-700 text-accent tabular-nums">{total}</span> prior
          breach{total === 1 ? "" : "es"} against this target and evolved fresh
          variations from them.
        </p>
        <ul className="flex flex-col gap-1">
          {recalls.map((r, i) => (
            <li
              key={i}
              className="flex items-center justify-between text-[11.5px] text-muted"
            >
              <span>{r.category}</span>
              <span className="tabular-nums text-dim">
                +{r.count} recalled
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
