export default function App() {
  return (
    <div className="mx-auto max-w-5xl px-5 py-6 sm:px-8 sm:py-10">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-5">
        <h1 className="text-lg font-semibold tracking-tight">Day-Ahead Wind Forecast Monitor</h1>
        <div className="flex flex-wrap gap-3 text-sm">
          <label className="flex flex-col gap-1">
            <span className="text-muted">Auction</span>
            <select className="rounded border border-rule bg-white px-3 py-2">
              <option>EPEX 60-min (09:20)</option>
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-muted">Delivery day</span>
            <select className="rounded border border-rule bg-white px-3 py-2">
              <option>Thu 15 Jan</option>
            </select>
          </label>
        </div>
      </header>

      <main>
        <section className="border-b border-rule py-10" aria-label="Recommendation">
          <p className="text-3xl font-semibold leading-tight sm:text-5xl" style={{ fontStretch: '112%' }}>
            For Thu 15 Jan, count on about 7,230 MW of wind.
          </p>
          <p className="mt-4 max-w-2xl text-muted">
            Placeholder: the forecast you had at 09:20, how much we discount it, and what actually came.
          </p>
        </section>

        <section className="border-b border-rule py-8">
          <h2 className="font-semibold">Hour by hour</h2>
          <div className="mt-4 grid h-72 place-items-center rounded bg-white/60 text-muted">
            Hourly chart
          </div>
        </section>

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