// Restock recommendation logic for the Restocking view

const TREND_PRIORITY = { increasing: 0, stable: 1, decreasing: 2 }
const SAFETY_BUFFER = 0.1

// Units to reorder for one forecast: the demand gap, or a 10% safety buffer if larger
export function suggestedQuantity(forecast) {
  const gap = forecast.forecasted_demand - forecast.current_demand
  return Math.max(gap, Math.ceil(forecast.forecasted_demand * SAFETY_BUFFER))
}

// Cost of restocking every forecast item at its suggested quantity
export function totalSuggestedCost(forecasts) {
  return forecasts.reduce((sum, f) => sum + suggestedQuantity(f) * f.unit_cost, 0)
}

// Greedily fill the budget: increasing trends first, then largest demand gap.
// The first item that does not fully fit is partially filled; later items are skipped.
export function recommendRestock(forecasts, budget) {
  const ranked = [...forecasts].sort((a, b) => {
    const trendDiff = (TREND_PRIORITY[a.trend] ?? 3) - (TREND_PRIORITY[b.trend] ?? 3)
    if (trendDiff !== 0) return trendDiff
    return (b.forecasted_demand - b.current_demand) - (a.forecasted_demand - a.current_demand)
  })

  const items = []
  let remaining = budget
  for (const forecast of ranked) {
    const suggested = suggestedQuantity(forecast)
    const affordable = Math.floor(remaining / forecast.unit_cost)
    const quantity = Math.min(suggested, affordable)
    if (quantity <= 0) break

    const lineTotal = Math.round(quantity * forecast.unit_cost * 100) / 100
    items.push({
      ...forecast,
      suggested_quantity: suggested,
      quantity,
      line_total: lineTotal,
      partial: quantity < suggested
    })
    remaining -= lineTotal
    if (quantity < suggested) break
  }

  const total = Math.round(items.reduce((sum, i) => sum + i.line_total, 0) * 100) / 100
  return { items, total, remaining: Math.max(budget - total, 0) }
}
