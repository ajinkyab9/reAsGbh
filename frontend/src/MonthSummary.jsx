import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  Rectangle,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fmtDate, fmtMW, fmtPct, fmtSignedMW } from './format'
import { COLORS } from './theme'

const axisTick = { fill: COLORS.muted, fontSize: 12 }
const thousands = (v) => v.toLocaleString('en-GB')

/** month accuracy: four headline figures, what the buffer achieved, and a daily chart */
export default function MonthSummary({ data, quantile, selectedDay, onSelectDay }) {
  const { metrics, buffer, days } = data
  const first = days[0].deliveryDate
  const last = days.at(-1).deliveryDate

  const figures = [
    { value: fmtSignedMW(metrics.bias_mw), label: 'average over-forecast (bias)' },
    { value: fmtMW(metrics.mae_mw), label: `typical miss (MAE), ${fmtPct(metrics.nmae_pct)} of output` },
    { value: fmtMW(metrics.rmse_mw), label: 'RMSE, weights the big misses' },
    { value: fmtPct(metrics.pct_hours_over_forecast), label: 'of hours forecast too high' },
  ]

  return (
    <section className="py-8">
      <h2 className="font-semibold">
        How the forecast performed, {fmtDate(first)} to {fmtDate(last)}
      </h2>

      <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-4">
        {figures.map((f) => (
          <div key={f.label}>
            <dt className="sr-only">{f.label}</dt>
            <dd className="text-2xl font-semibold sm:text-3xl">{f.value}</dd>
            <dd className="mt-1 text-sm text-muted">{f.label}</dd>
          </div>
        ))}
      </dl>

      <p className="mt-6 max-w-2xl text-muted">
        Sized only from earlier days, the buffer averaged{' '}
        <span className="text-risk">{fmtMW(buffer.mean_buffer_mw)}</span> and covered{' '}
        {fmtPct(buffer.coverage_pct)} of hours, against a {fmtPct(quantile * 100)} target.
        Correcting for the bias alone would have cut the typical miss from{' '}
        {fmtMW(buffer.mae_raw_mw)} to {fmtMW(buffer.mae_bias_corrected_mw)}.
      </p>

      <h3 className="mt-8 text-sm font-semibold">Average error by delivery day</h3>
      <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted">
        <li className="flex items-center gap-2">
          <span className="inline-block h-3 w-3" style={{ background: COLORS.risk }} aria-hidden="true" />
          Forecast too high
        </li>
        <li className="flex items-center gap-2">
          <span className="inline-block h-3 w-3" style={{ background: COLORS.forecast }} aria-hidden="true" />
          Forecast too low
        </li>
        <li className="flex items-center gap-2">
          <svg width="20" height="4" aria-hidden="true">
            <line x1="0" y1="2" x2="20" y2="2" stroke={COLORS.ink} strokeWidth="2" strokeDasharray="5 3" />
          </svg>
          Buffer used that day
        </li>
        <li>Click a day to open it above.</li>
      </ul>

      <div
        className="mt-3 h-64 sm:h-72"
        role="img"
        aria-label="Average forecast error for each delivery day, with the buffer used that day."
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={days} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={COLORS.rule} strokeDasharray="2 4" vertical={false} />
            <XAxis
              dataKey="deliveryDate"
              tickFormatter={fmtDate}
              interval={4}
              tick={axisTick}
              tickLine={false}
              axisLine={{ stroke: COLORS.rule }}
            />
            <YAxis tickFormatter={thousands} tick={axisTick} tickLine={false} axisLine={false} width={56} />
            <ReferenceLine y={0} stroke={COLORS.muted} />
            <Tooltip content={<DayTooltip />} cursor={{ fill: COLORS.rule, fillOpacity: 0.3 }} />
            <Bar
              dataKey="bias_mw"
              isAnimationActive={false}
              cursor="pointer"
              onClick={(entry) => onSelectDay(entry.payload.deliveryDate)}
              shape={(props) => {
                const d = props.payload
                const selected = d.deliveryDate === selectedDay
                return (
                  <Rectangle
                    {...props}
                    fill={d.bias_mw >= 0 ? COLORS.risk : COLORS.forecast}
                    fillOpacity={selected ? 1 : 0.55}
                    stroke={selected ? COLORS.ink : 'none'}
                  />
                )
              }}
            />
            <Line
              dataKey="buffer_mw"
              type="stepAfter"
              stroke={COLORS.ink}
              strokeWidth={2}
              strokeDasharray="5 3"
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

function DayTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded border border-rule bg-white px-3 py-2 text-sm shadow-sm">
      <p className="font-semibold">{fmtDate(d.deliveryDate)}</p>
      <p>Average error {fmtSignedMW(d.bias_mw)}</p>
      <p>Typical miss {fmtMW(d.mae_mw)}</p>
      {d.buffer_mw != null ? (
        <p>
          Buffer {fmtMW(d.buffer_mw)}, covered {fmtPct(d.coverage_pct)} of hours
        </p>
      ) : (
        <p className="text-muted">No buffer yet (too few earlier days)</p>
      )}
    </div>
  )
}