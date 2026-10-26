import { useState } from 'react'
import { apiPath } from './api'
import { fmtDay } from './format'
import Headline from './Headline'
import HourlyChart from './HourlyChart'
import { useApi } from './useApi'

export default function App() {
  const meta = useApi('/meta')
  const [cutoffChoice, setCutoff] = useState(null)
  const [dayChoice, setDay] = useState(null)

  // uses the default cutoff from API until a user selects otherwise
  const cutoff = cutoffChoice ?? meta.data?.default_cutoff
  const day = dayChoice ?? meta.data?.days.at(-1)

  const summary = useApi(cutoff ? apiPath('/summary', { cutoff }) : null)
  const dayData = useApi(day && cutoff ? apiPath('/day', { date: day, cutoff }) : null)

  if (meta.error) {
    return (
      <p className="mx-auto max-w-5xl p-8">
        Couldn&rsquo;t load data from the API ({meta.error.message}). Check that the backend is
        running on port 8000.
      </p>
    )
  }
  if (!meta.data) return <p className="mx-auto max-w-5xl p-8 text-muted">Loading January 2026 data…</p>

  return (
    <div className="mx-auto max-w-5xl px-5 py-6 sm:px-8 sm:py-10">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-5">
        <h1 className="text-lg font-semibold tracking-tight">Day Ahead Wind Forecast Monitor</h1>
        <div className="flex flex-wrap gap-3 text-sm">
          <label className="flex flex-col gap-1">
            <span className="text-muted">Auction</span>
            <select
              className="rounded border border-rule bg-white px-3 py-2"
              value={cutoff}
              onChange={(e) => setCutoff(e.target.value)}
            >
              {meta.data.cutoffs.map((c) => (
                <option key={c.time} value={c.time}>
                  {c.label} ({c.time})
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-muted">Delivery day</span>
            <select
              className="rounded border border-rule bg-white px-3 py-2"
              value={day}
              onChange={(e) => setDay(e.target.value)}
            >
              {meta.data.days.map((d) => (
                <option key={d} value={d}>
                  {fmtDay(d)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <main className={dayData.loading || summary.loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
        {dayData.error && (
          <p className="py-10">Couldn&rsquo;t load {fmtDay(day)} ({dayData.error.message}).</p>
        )}
        {dayData.data && (
          <Headline day={day} data={dayData.data} quantile={meta.data.buffer_quantile} />
        )}

        {dayData.data && (
          <section className="border-b border-rule py-8">
            <h2 className="font-semibold">Hour by hour, {fmtDay(day)}</h2>
            <HourlyChart data={dayData.data} cutoffTime={cutoff} />
          </section>
        )}

        <section className="py-8">
          <h2 className="font-semibold">How the forecast performed, 2 Jan to 1 Feb</h2>
          <div className="mt-4 grid h-56 place-items-center rounded bg-white/60 text-muted">
            Month figures and daily chart
          </div>
        </section>
      </main>
    </div>
  )
}