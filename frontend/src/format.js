const wholeNumber = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })

/** 11609.6 -> "11,610 MW" */
export const fmtMW = (value) => `${wholeNumber.format(value)} MW`

/** round to the nearest 10 MW for headline figures, so false precision isnt  */
export const round10 = (value) => Math.round(value / 10) * 10

const dayFormat = new Intl.DateTimeFormat('en-GB', {
  weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC',
})
/** "2026-01-15" -> "Thu 15 Jan" delivery date without involving timezone */
export const fmtDay = (isoDate) => dayFormat.format(new Date(`${isoDate}T00:00:00Z`))

const ukTime = new Intl.DateTimeFormat('en-GB', {
  hour: '2-digit', minute: '2-digit', timeZone: 'Europe/London',
})
const ukDay = new Intl.DateTimeFormat('en-GB', {
  weekday: 'short', day: 'numeric', month: 'short', timeZone: 'Europe/London',
})
/** "2026-01-14T07:30:00Z" "07:30" in UK time */
export const fmtTimeUK = (isoTimestamp) => ukTime.format(new Date(isoTimestamp))
/** "2026-01-14T09:20:00Z" "Wed 14 Jan" in UK time */
export const fmtDayUK = (isoTimestamp) => ukDay.format(new Date(isoTimestamp))

export const mean = (values) => values.reduce((a, b) => a + b, 0) / values.length