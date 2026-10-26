import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fmtMW, fmtTimeUK } from './format'
import { COLORS } from './theme'

const axisTick = { fill: COLORS.muted, fontSize: 12 }
const thousands = (v) => v.toLocaleString('en-GB')

/** Forecast at the cutoff, what to count on after the buffer, and what actually came
 * cutoff forecastm what to count on after buffer and what is actual requirement. */
export default function HourlyChart({ data, cutoffTime }) {
  const buffer = data.buffer_mw
  const rows = data.hours.map((h) => {
    const countOn = buffer == null ? null : Math.max(h.forecast_mw - buffer, 0)
    return {
      hour: fmtTimeUK(h.startTime),
      forecast: h.forecast_mw,
      actual: h.actual_mw,
      countOn,
      band: countOn == null ? null : [countOn, h.forecast_mw],
    }
  })

  return (
    <>
      <Legend cutoffTime={cutoffTime} hasBuffer={buffer != null} />
      <div
        className="mt-3 h-72 sm:h-80"
        role="img"
        aria-label={`Hourly wind: forecast at ${cutoffTime}${buffer == null ? '' : ', what to count on after the buffer'}, and actual output.`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={COLORS.rule} strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="hour" interval={2} tick={axisTick} tickLine={false} axisLine={{ stroke: COLORS.rule }} />
            <YAxis
              domain={[0, 'auto']}
              tickFormatter={thousands}
              tick={axisTick}
              tickLine={false}
              axisLine={false}
              width={56}
            />
            <Tooltip content={<HourTooltip />} />
            {buffer != null && (
              <Area dataKey="band" stroke="none" fill={COLORS.risk} fillOpacity={0.12} isAnimationActive={false} />
            )}
            {buffer != null && (
              <Line dataKey="countOn" stroke={COLORS.risk} strokeWidth={2} strokeDasharray="6 4" dot={false} isAnimationActive={false} />
            )}
            <Line dataKey="forecast" stroke={COLORS.forecast} strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line dataKey="actual" stroke={COLORS.ink} strokeWidth={2} dot={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}

function Legend({ cutoffTime, hasBuffer }) {
  const items = [
    { label: `Forecast you had at ${cutoffTime}`, color: COLORS.forecast },
    ...(hasBuffer ? [{ label: 'Count on (forecast minus buffer)', color: COLORS.risk, dashed: true }] : []),
    { label: 'Actual output', color: COLORS.ink },
  ]
  return (
    <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-2">
          <svg width="20" height="4" aria-hidden="true">
            <line
              x1="0" y1="2" x2="20" y2="2"
              stroke={item.color} strokeWidth="2.5"
              strokeDasharray={item.dashed ? '5 3' : undefined}
            />
          </svg>
          {item.label}
        </li>
      ))}
    </ul>
  )
}

function HourTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  return (
    <div className="rounded border border-rule bg-white px-3 py-2 text-sm shadow-sm">
      <p className="font-semibold">{row.hour} UK</p>
      <p style={{ color: COLORS.forecast }}>Forecast {fmtMW(row.forecast)}</p>
      {row.countOn != null && <p style={{ color: COLORS.risk }}>Count on {fmtMW(row.countOn)}</p>}
      <p>Actual {fmtMW(row.actual)}</p>
    </div>
  )
}