import { fmtDay, fmtDayUK, fmtMW, fmtTimeUK, mean, round10 } from './format'

/** at a glance typoe answer in a single sentencce with reasoning */
export default function Headline({ day, data, quantile }) {
  const { metrics, hours, buffer_mw: buffer, runs_used: runs, cutoff_utc: cutoff } = data
  const deadline = `${fmtTimeUK(cutoff)} on ${fmtDayUK(cutoff)}`
  const published = fmtTimeUK(runs.at(-1))
  const forecast = metrics.mean_forecast_mw
  const actual = metrics.mean_actual_mw

  if (buffer == null) {
    return (
      <section className="border-b border-rule py-10" aria-label="Recommendation">
        <p className="text-3xl font-semibold leading-tight sm:text-5xl" style={{ fontStretch: '112%' }}>
          For {fmtDay(day)}, the forecast says about {fmtMW(round10(forecast))} of wind.
        </p>
        <p className="mt-4 max-w-2xl text-muted">
          At the deadline ({deadline}), the latest forecast (published {published}) averaged{' '}
          {fmtMW(forecast)}. There aren&rsquo;t enough earlier days yet to size a safety
          discount. Actual output averaged {fmtMW(actual)}.
        </p>
      </section>
    )
  }

  const countOnByHour = hours.map((h) => Math.max(h.forecast_mw - buffer, 0))
  const countOn = mean(countOnByHour)
  const hoursMet = hours.filter((h, i) => h.actual_mw >= countOnByHour[i]).length

  return (
    <section className="border-b border-rule py-10" aria-label="Recommendation">
      <p className="text-3xl font-semibold leading-tight sm:text-5xl" style={{ fontStretch: '112%' }}>
        For {fmtDay(day)}, count on about {fmtMW(round10(countOn))} of wind.
      </p>
      <p className="mt-4 max-w-2xl text-muted">
        At the deadline ({deadline}), the latest forecast (published {published}) averaged{' '}
        {fmtMW(forecast)}. We discount it by <span className="text-risk">{fmtMW(buffer)}</span>,
        the margin that would have covered {Math.round(quantile * 100)}% of hours on the days
        before.
      </p>
      <p className="mt-2 max-w-2xl text-muted">
        Actual output averaged {fmtMW(actual)}, and met that level in {hoursMet} of{' '}
        {hours.length} hours.
      </p>
    </section>
  )
}