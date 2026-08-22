/** Market structure analysis engine.

NO_DEPLOYMENT_SIGNAL -- This module is descriptive only. All outputs
describe historical price structure for human review. Nothing produced
by this module constitutes a trading signal, buy/sell recommendation,
or claim of predictive power.

All functions are deterministic and stateless. No future-data access:
every output at index i depends only on data at or before i.
*/

export type SwingType = 'high' | 'low';
export type StructureBreakType = 'bos_bull' | 'bos_bear' | 'choch_bull' | 'choch_bear';
export type MarketRegime = 'uptrend' | 'downtrend' | 'ranging';

export type SwingPoint = {
  index: number;
  price: number;
  swing_type: SwingType;
};

export type StructureBreak = {
  index: number;
  price: number;
  break_type: StructureBreakType;
  reference_index: number;
  reference_price: number;
};

export type LiquidityLevel = {
  index: number;
  price: number;
  swing_type: SwingType;
  swept: boolean;
  swept_at_index: number | null;
};

export type SRLevel = {
  level: number;
  type: 'support' | 'resistance';
  touches: number;
  indices: number[];
};

function validateLengths(...arrays: number[][]): void {
  if (arrays.length === 0) return;
  const lengths = arrays.map((a) => a.length);
  if (new Set(lengths).size > 1) {
    throw new Error(`Array length mismatch: ${lengths}`);
  }
}

export function detectSwingPoints(
  highs: number[],
  lows: number[],
  left: number = 3,
  right: number = 3,
): SwingPoint[] {
  validateLengths(highs, lows);
  const n = highs.length;
  if (n === 0) return [];

  const swings: SwingPoint[] = [];

  for (let i = 0; i < n; i++) {
    const leftStart = Math.max(0, i - left);
    const rightEnd = Math.min(n - 1, i + right);

    let leftOk = true;
    for (let j = leftStart; j < i; j++) {
      if (highs[i] <= highs[j]) {
        leftOk = false;
        break;
      }
    }
    if (leftOk) {
      let rightOk = true;
      for (let j = i + 1; j <= rightEnd; j++) {
        if (highs[i] <= highs[j]) {
          rightOk = false;
          break;
        }
      }
      if (rightOk) {
        swings.push({ index: i, price: highs[i], swing_type: 'high' });
      }
    }

    let leftOkLow = true;
    for (let j = leftStart; j < i; j++) {
      if (lows[i] >= lows[j]) {
        leftOkLow = false;
        break;
      }
    }
    if (leftOkLow) {
      let rightOkLow = true;
      for (let j = i + 1; j <= rightEnd; j++) {
        if (lows[i] >= lows[j]) {
          rightOkLow = false;
          break;
        }
      }
      if (rightOkLow) {
        swings.push({ index: i, price: lows[i], swing_type: 'low' });
      }
    }
  }

  swings.sort((a, b) => a.index - b.index);
  return swings;
}

export function classifySwingSequence(
  swings: SwingPoint[],
): [SwingPoint, string][] {
  if (swings.length === 0) return [];

  let lastHigh: SwingPoint | null = null;
  let lastLow: SwingPoint | null = null;
  const result: [SwingPoint, string][] = [];

  for (const sw of swings) {
    let label: string;
    if (sw.swing_type === 'high') {
      if (lastHigh === null) {
        label = 'first';
      } else if (sw.price > lastHigh.price) {
        label = 'HH';
      } else if (sw.price < lastHigh.price) {
        label = 'LH';
      } else {
        label = 'EQH';
      }
      result.push([sw, label]);
      lastHigh = sw;
    } else {
      if (lastLow === null) {
        label = 'first';
      } else if (sw.price > lastLow.price) {
        label = 'HL';
      } else if (sw.price < lastLow.price) {
        label = 'LL';
      } else {
        label = 'EQL';
      }
      result.push([sw, label]);
      lastLow = sw;
    }
  }

  return result;
}

export function detectStructureBreaks(
  highs: number[],
  lows: number[],
  closes: number[],
  swings: SwingPoint[],
  left: number = 3,
  right: number = 3,
): StructureBreak[] {
  validateLengths(highs, lows, closes);
  const n = closes.length;
  if (n === 0 || swings.length === 0) return [];

  const classified = classifySwingSequence(swings);

  const brokenLevels = new Set<number>();
  const breaks: StructureBreak[] = [];
  let trendState: string | null = null;
  let lastLhIndex: number | null = null;
  let lastHlIndex: number | null = null;

  for (const [sw, label] of classified) {
    if (sw.swing_type === 'high') {
      if (label === 'HH') {
        trendState = 'uptrend';
      } else if (label === 'LH') {
        lastLhIndex = sw.index;
        if (trendState === 'uptrend') {
          trendState = 'downtrend_start';
        } else if (trendState !== 'downtrend') {
          trendState = 'downtrend';
        }
      }
    } else {
      if (label === 'HL') {
        lastHlIndex = sw.index;
        trendState = 'uptrend';
      } else if (label === 'LL') {
        if (trendState === 'downtrend') {
          trendState = 'uptrend_start';
        } else if (trendState !== 'uptrend') {
          trendState = 'downtrend';
        }
      }
    }
  }

  for (let i = 0; i < n; i++) {
    let breakFound = false;

    for (let k = swings.length - 1; k >= 0; k--) {
      const sw = swings[k];
      if (sw.swing_type !== 'high') continue;
      if (sw.index >= i || brokenLevels.has(sw.index)) continue;
      if (closes[i] > sw.price) {
        const isChoch =
          lastLhIndex !== null &&
          sw.index <= lastLhIndex &&
          (trendState === 'downtrend' || trendState === 'downtrend_start');
        const bt: StructureBreakType = isChoch ? 'choch_bull' : 'bos_bull';
        breaks.push({
          index: i,
          price: closes[i],
          break_type: bt,
          reference_index: sw.index,
          reference_price: sw.price,
        });
        brokenLevels.add(sw.index);
        breakFound = true;
        break;
      }
    }

    if (breakFound) continue;

    for (let k = swings.length - 1; k >= 0; k--) {
      const sw = swings[k];
      if (sw.swing_type !== 'low') continue;
      if (sw.index >= i || brokenLevels.has(sw.index)) continue;
      if (closes[i] < sw.price) {
        const isChoch =
          lastHlIndex !== null &&
          sw.index <= lastHlIndex &&
          (trendState === 'uptrend' || trendState === 'uptrend_start');
        const bt: StructureBreakType = isChoch ? 'choch_bear' : 'bos_bear';
        breaks.push({
          index: i,
          price: closes[i],
          break_type: bt,
          reference_index: sw.index,
          reference_price: sw.price,
        });
        brokenLevels.add(sw.index);
        break;
      }
    }
  }

  return breaks;
}

export function detectSupportResistance(
  highs: number[],
  lows: number[],
  closes: number[],
  swings: SwingPoint[],
  tolerance: number = 0.005,
): SRLevel[] {
  validateLengths(highs, lows, closes);
  if (swings.length === 0) return [];

  const sortedSwings = [...swings].sort((a, b) => a.price - b.price);
  const clusters: SwingPoint[][] = [];
  let currentCluster: SwingPoint[] = [sortedSwings[0]];

  for (let i = 1; i < sortedSwings.length; i++) {
    const sw = sortedSwings[i];
    const refPrice = currentCluster[0].price;
    if (refPrice === 0 || Math.abs(sw.price - refPrice) / Math.abs(refPrice) <= tolerance) {
      currentCluster.push(sw);
    } else {
      clusters.push(currentCluster);
      currentCluster = [sw];
    }
  }
  clusters.push(currentCluster);

  const results: SRLevel[] = [];
  for (const cluster of clusters) {
    if (cluster.length < 2) continue;

    const avgPrice = cluster.reduce((sum, sw) => sum + sw.price, 0) / cluster.length;
    const anyHigh = cluster.some((sw) => sw.swing_type === 'high');
    const anyLow = cluster.some((sw) => sw.swing_type === 'low');

    let levelType: 'support' | 'resistance';
    if (anyHigh && !anyLow) {
      levelType = 'resistance';
    } else if (anyLow && !anyHigh) {
      levelType = 'support';
    } else {
      levelType = 'resistance';
    }

    results.push({
      level: avgPrice,
      type: levelType,
      touches: cluster.length,
      indices: cluster.map((sw) => sw.index),
    });
  }

  return results;
}

export function detectLiquidity(
  highs: number[],
  lows: number[],
  closes: number[],
  swings: SwingPoint[],
): LiquidityLevel[] {
  validateLengths(highs, lows, closes);
  const n = highs.length;
  if (n === 0) return [];

  const levels: LiquidityLevel[] = [];

  for (const sw of swings) {
    let swept = false;
    let sweptAt: number | null = null;

    if (sw.swing_type === 'high') {
      for (let j = sw.index + 1; j < n; j++) {
        if (highs[j] > sw.price) {
          swept = true;
          sweptAt = j;
          break;
        }
      }
    } else {
      for (let j = sw.index + 1; j < n; j++) {
        if (lows[j] < sw.price) {
          swept = true;
          sweptAt = j;
          break;
        }
      }
    }

    levels.push({
      index: sw.index,
      price: sw.price,
      swing_type: sw.swing_type,
      swept,
      swept_at_index: sweptAt,
    });
  }

  return levels;
}

export function classifyMarketRegime(
  swings: SwingPoint[],
  closes: number[],
  lookback: number = 20,
): MarketRegime {
  if (swings.length === 0 || closes.length === 0) return 'ranging';

  const classified = classifySwingSequence(swings);
  const n = closes.length;
  const windowStart = Math.max(0, n - lookback);

  const recent = classified.filter(([sw]) => sw.index >= windowStart);

  if (recent.length === 0) return 'ranging';

  const bullish = recent.filter(([, label]) => label === 'HH' || label === 'HL').length;
  const bearish = recent.filter(([, label]) => label === 'LH' || label === 'LL').length;
  const total = recent.length;

  const bullPct = bullish / total;
  const bearPct = bearish / total;

  if (bullPct > 0.6) return 'uptrend';
  if (bearPct > 0.6) return 'downtrend';
  return 'ranging';
}

export function analyzeStructure(
  highs: number[],
  lows: number[],
  closes: number[],
  left: number = 3,
  right: number = 3,
): {
  swings: SwingPoint[];
  classified: [SwingPoint, string][];
  breaks: StructureBreak[];
  supportResistance: SRLevel[];
  liquidity: LiquidityLevel[];
  regime: MarketRegime;
} {
  validateLengths(highs, lows, closes);

  const swings = detectSwingPoints(highs, lows, left, right);
  const classified = classifySwingSequence(swings);
  const breaks = detectStructureBreaks(highs, lows, closes, swings, left, right);
  const supportResistance = detectSupportResistance(highs, lows, closes, swings);
  const liquidity = detectLiquidity(highs, lows, closes, swings);
  const regime = classifyMarketRegime(swings, closes);

  return { swings, classified, breaks, supportResistance, liquidity, regime };
}
