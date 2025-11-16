/**
 * Enhanced Chart Implementation for Options Plunge
 * Features:
 * - Premarket/Afterhours data toggle with visual indicators
 * - Continuous chart display (no gaps for closed sessions)
 * - Smart filtering of empty/zero-volume bars
 * - Better extended hours visibility
 */

// Global chart state management
let chartState = {
    symbol: null,
    timeframe: null,
    data: {
        full: null,      // All data including extended hours
        regular: null,   // Regular trading hours only
        premarket: null, // Premarket data only
        afterhours: null // After-hours data only
    },
    display: {
        showPremarket: true,
        showAfterhours: true,
        hideClosed: true,
        highlightExtended: true
    },
    layout: null,
    el: null
};

// Enhanced rangebreaks configuration for continuous display
function buildEnhancedRangebreaks(options = {}) {
    const { 
        showPremarket = true, 
        showAfterhours = true, 
        hideClosed = true,
        timeframe = '1d' 
    } = options;
    
    if (!hideClosed) return [];
    
    const breaks = [];
    
    // For daily charts, only hide weekends
    if (timeframe === '1d') {
        breaks.push({ 
            pattern: 'day of week', 
            bounds: ['sat', 'mon'],
            name: 'weekend'
        });
        return breaks;
    }
    
    // For intraday charts, build comprehensive breaks
    
    // 1. Always hide weekends
    breaks.push({ 
        pattern: 'day of week', 
        bounds: ['sat', 'mon'],
        name: 'weekend'
    });
    
    // 2. Configure session breaks based on user preferences
    if (!showPremarket && !showAfterhours) {
        // Hide everything outside regular trading hours (9:30 AM - 4:00 PM ET)
        breaks.push(
            { pattern: 'hour', bounds: [16, 24], name: 'overnight' },  // 4 PM to midnight
            { pattern: 'hour', bounds: [0, 9.5], name: 'pre-open' }    // Midnight to 9:30 AM
        );
    } else if (!showPremarket && showAfterhours) {
        // Hide premarket but show afterhours (hide midnight to 9:30 AM)
        breaks.push(
            { pattern: 'hour', bounds: [20, 24], name: 'late-night' }, // 8 PM to midnight
            { pattern: 'hour', bounds: [0, 9.5], name: 'pre-open' }    // Midnight to 9:30 AM
        );
    } else if (showPremarket && !showAfterhours) {
        // Show premarket but hide afterhours (hide 4 PM to 4 AM)
        breaks.push(
            { pattern: 'hour', bounds: [16, 24], name: 'after-close' }, // 4 PM to midnight
            { pattern: 'hour', bounds: [0, 4], name: 'overnight' }      // Midnight to 4 AM
        );
    } else {
        // Show both premarket and afterhours (only hide overnight 8 PM to 4 AM)
        breaks.push(
            { pattern: 'hour', bounds: [20, 24], name: 'late-night' }, // 8 PM to midnight
            { pattern: 'hour', bounds: [0, 4], name: 'overnight' }     // Midnight to 4 AM
        );
    }
    
    return breaks;
}

// Enhanced data filtering to separate regular/extended hours
function separateSessionData(data) {
    if (!data || !data.t) return { regular: null, premarket: null, afterhours: null };
    
    const regular = { t: [], o: [], h: [], l: [], c: [], v: [] };
    const premarket = { t: [], o: [], h: [], l: [], c: [], v: [] };
    const afterhours = { t: [], o: [], h: [], l: [], c: [], v: [] };
    
    for (let i = 0; i < data.t.length; i++) {
        const timestamp = data.t[i];
        const date = new Date(timestamp);
        const hours = date.getUTCHours();
        const minutes = date.getUTCMinutes();
        const totalMinutes = hours * 60 + minutes;
        
        // Convert to ET (assuming UTC timestamps)
        const etHours = (hours - 5 + 24) % 24; // Simple ET conversion (adjust for DST as needed)
        const etTotalMinutes = etHours * 60 + minutes;
        
        // Classify based on session times (ET)
        const isPremarket = etTotalMinutes >= 240 && etTotalMinutes < 570;  // 4:00 AM - 9:30 AM
        const isRegular = etTotalMinutes >= 570 && etTotalMinutes < 960;    // 9:30 AM - 4:00 PM
        const isAfterhours = etTotalMinutes >= 960 && etTotalMinutes < 1200; // 4:00 PM - 8:00 PM
        
        const bar = {
            t: data.t[i],
            o: data.o[i],
            h: data.h[i],
            l: data.l[i],
            c: data.c[i],
            v: data.v?.[i] || 0
        };
        
        // Skip bars with zero volume or invalid prices
        if (bar.v === 0 && !isRegular) continue; // Keep zero-volume bars during regular hours
        if (!Number.isFinite(bar.o) || !Number.isFinite(bar.h) || 
            !Number.isFinite(bar.l) || !Number.isFinite(bar.c)) continue;
        
        if (isPremarket) {
            Object.keys(bar).forEach(key => premarket[key].push(bar[key]));
        } else if (isRegular) {
            Object.keys(bar).forEach(key => regular[key].push(bar[key]));
        } else if (isAfterhours) {
            Object.keys(bar).forEach(key => afterhours[key].push(bar[key]));
        }
    }
    
    return { regular, premarket, afterhours };
}

// Build combined dataset based on display preferences
function buildDisplayData(chartState) {
    const { regular, premarket, afterhours } = chartState.data;
    const { showPremarket, showAfterhours } = chartState.display;
    
    const combined = { t: [], o: [], h: [], l: [], c: [], v: [], session: [] };
    
    // Helper to add data with session markers
    const addData = (data, sessionType) => {
        if (!data || !data.t) return;
        for (let i = 0; i < data.t.length; i++) {
            combined.t.push(data.t[i]);
            combined.o.push(data.o[i]);
            combined.h.push(data.h[i]);
            combined.l.push(data.l[i]);
            combined.c.push(data.c[i]);
            combined.v.push(data.v[i]);
            combined.session.push(sessionType);
        }
    };
    
    // Combine all data in chronological order
    const allData = [];
    
    if (showPremarket && premarket) {
        premarket.t.forEach((t, i) => {
            allData.push({
                t, o: premarket.o[i], h: premarket.h[i],
                l: premarket.l[i], c: premarket.c[i],
                v: premarket.v[i], session: 'premarket'
            });
        });
    }
    
    if (regular) {
        regular.t.forEach((t, i) => {
            allData.push({
                t, o: regular.o[i], h: regular.h[i],
                l: regular.l[i], c: regular.c[i],
                v: regular.v[i], session: 'regular'
            });
        });
    }
    
    if (showAfterhours && afterhours) {
        afterhours.t.forEach((t, i) => {
            allData.push({
                t, o: afterhours.o[i], h: afterhours.h[i],
                l: afterhours.l[i], c: afterhours.c[i],
                v: afterhours.v[i], session: 'afterhours'
            });
        });
    }
    
    // Sort by timestamp
    allData.sort((a, b) => a.t - b.t);
    
    // Build final arrays
    allData.forEach(bar => {
        Object.keys(bar).forEach(key => {
            combined[key].push(bar[key]);
        });
    });
    
    return combined;
}

// Create Plotly traces with session-based coloring
function createEnhancedTraces(data, displayOptions) {
    const traces = [];
    
    if (!data || !data.t || data.t.length === 0) return traces;
    
    const { highlightExtended } = displayOptions;
    
    if (highlightExtended && data.session) {
        // Create separate traces for each session type for different coloring
        const sessions = {
            premarket: { 
                indices: [], 
                color: { increasing: '#90EE90', decreasing: '#FFB6C1' }, // Light green/pink
                name: 'Pre-Market',
                opacity: 0.7
            },
            regular: { 
                indices: [], 
                color: { increasing: '#26a69a', decreasing: '#ef5350' }, // Standard colors
                name: 'Regular Hours',
                opacity: 1
            },
            afterhours: { 
                indices: [], 
                color: { increasing: '#87CEEB', decreasing: '#DDA0DD' }, // Light blue/plum
                name: 'After-Hours',
                opacity: 0.7
            }
        };
        
        // Group indices by session
        data.session.forEach((session, i) => {
            if (sessions[session]) {
                sessions[session].indices.push(i);
            }
        });
        
        // Create a trace for each session
        Object.entries(sessions).forEach(([sessionType, config]) => {
            if (config.indices.length > 0) {
                const trace = {
                    type: 'candlestick',
                    x: config.indices.map(i => new Date(data.t[i])),
                    open: config.indices.map(i => data.o[i]),
                    high: config.indices.map(i => data.h[i]),
                    low: config.indices.map(i => data.l[i]),
                    close: config.indices.map(i => data.c[i]),
                    name: config.name,
                    increasing: { 
                        line: { color: config.color.increasing, width: 1 }
                    },
                    decreasing: { 
                        line: { color: config.color.decreasing, width: 1 }
                    },
                    opacity: config.opacity,
                    showlegend: true
                };
                traces.push(trace);
            }
        });
    } else {
        // Single trace for all data
        const trace = {
            type: 'candlestick',
            x: data.t.map(ts => new Date(ts)),
            open: data.o,
            high: data.h,
            low: data.l,
            close: data.c,
            name: chartState.symbol || 'Price',
            increasing: { line: { color: '#26a69a', width: 1 } },
            decreasing: { line: { color: '#ef5350', width: 1 } },
            showlegend: false
        };
        traces.push(trace);
    }
    
    return traces;
}

// Enhanced chart loading function
async function loadEnhancedChart() {
    // Check if chart element exists
    const chartEl = document.getElementById('chart') || document.getElementById('tradeChart');
    if (!chartEl) {
        console.error('Chart element #chart not found in DOM');
        alert('Chart container not found. Please refresh the page.');
        return;
    }
    
    const symbol = (document.getElementById('symbol-input')?.value || 'AAPL').toUpperCase();
    const timeframe = document.getElementById('chart-timeframe')?.value || '1d';
    
    // Get display preferences (default to false if controls don't exist)
    const showPremarket = document.getElementById('show-premarket')?.checked ?? false;
    const showAfterhours = document.getElementById('show-afterhours')?.checked ?? false;
    const hideClosed = document.getElementById('hide-closed')?.checked ?? true;
    const highlightExtended = document.getElementById('highlight-extended')?.checked ?? false;
    
    // Show loading message in chart
    chartEl.innerHTML = '<div class="text-center p-5"><i class="fas fa-spinner fa-spin fa-3x text-primary"></i><p class="mt-3">Loading chart data...</p></div>';
    
    // Update chart state
    chartState.symbol = symbol;
    chartState.timeframe = timeframe;
    chartState.display = { showPremarket, showAfterhours, hideClosed, highlightExtended };
    
    // Fetch data
    const params = new URLSearchParams({ symbol, tf: timeframe });
    if (timeframe === '1d') {
        const start = new Date(Date.now() - 3650*24*3600*1000).toISOString().slice(0,10);
        params.set('start', start);
    }
    
    try {
        const url = `/api/candles?${params.toString()}`;
        // show loading spinner if present
        const loadingEl = document.getElementById('chart-loading');
        if (loadingEl) loadingEl.classList.remove('d-none');
        const res = await fetch(url);
        let data;
        try {
            data = await res.json();
        } catch (e) {
            // Try text body for more detail
            let text = '';
            try { text = await res.text(); } catch (_) {}
            throw new Error(`Bad response from server (status ${res.status}) ${text ? `- ${text.slice(0, 200)}` : ''}`);
        }
        if (!res.ok) {
            throw new Error(data && data.error ? data.error : `HTTP ${res.status}`);
        }
        if (data && data.error) {
            throw new Error(data.error);
        }
        
        // Store full data
        chartState.data.full = data;
        
        let displayData;
        if (timeframe === '1d') {
            // Daily timeframe: no session separation; plot as a single trace
            displayData = { t: data.t, o: data.o, h: data.h, l: data.l, c: data.c, v: data.v || [] };
        } else {
            // Intraday: separate by sessions and build combined dataset
            const sessions = separateSessionData(data);
            chartState.data.regular = sessions.regular;
            chartState.data.premarket = sessions.premarket;
            chartState.data.afterhours = sessions.afterhours;
            displayData = buildDisplayData(chartState);
        }
        
        // Create traces
        const traces = createEnhancedTraces(displayData, chartState.display);
        
        // Build layout with enhanced rangebreaks
        const layout = {
            title: `${symbol} - ${timeframe.toUpperCase()}`,
            xaxis: {
                type: 'date',
                rangeslider: { visible: false },
                rangebreaks: buildEnhancedRangebreaks({
                    showPremarket,
                    showAfterhours,
                    hideClosed,
                    timeframe
                })
            },
            yaxis: {
                title: 'Price',
                side: 'right',
                fixedrange: false
            },
            margin: { l: 10, r: 80, t: 40, b: 40 },
            showlegend: highlightExtended,
            legend: {
                orientation: 'h',
                y: 1.02,
                x: 0.5,
                xanchor: 'center'
            },
            hovermode: 'x unified'
        };
        
        // Clear loading message
        chartEl.innerHTML = '';
        
        // Plot the chart
        const el = chartEl;
        await Plotly.newPlot(el, traces, layout, {
            responsive: true,
            displaylogo: false,
            modeBarButtonsToAdd: ['drawline', 'drawrect', 'eraseshape'],
            toImageButtonOptions: {
                format: 'png',
                filename: `${symbol}_${timeframe}_${new Date().toISOString().slice(0,10)}`,
                height: 800,
                width: 1200,
                scale: 1
            }
        });
        
        // Store element reference
        chartState.el = el;
        chartState.layout = layout;
        
        // Apply auto support/resistance overlays
        applyAutoSupportResistance(displayData, symbol, timeframe);
        
        // Add session info display
        updateSessionInfo(displayData);
        
    } catch (error) {
        console.error('Chart loading error:', error);
        // Inline error display
        if (chartEl) {
            chartEl.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Failed to load chart data: ${String(error.message || error)}
                </div>
            `;
        } else {
            alert(`Failed to load chart data: ${error.message}`);
        }
    }
    finally {
        const loadingEl = document.getElementById('chart-loading');
        if (loadingEl) loadingEl.classList.add('d-none');
    }
}

// Auto Support/Resistance overlay function
async function applyAutoSupportResistance(displayData, symbol, timeframe) {
    try {
        if (!displayData || !displayData.t || displayData.t.length < 30) {
            // Not enough data to compute meaningful levels
            return;
        }

        const { t, h, l, c } = displayData;
        const n = c.length;
        if (!n) return;

        const currentPrice = c[n - 1];
        const supportColor = '#007bff';   // blue
        const resistanceColor = '#fd7e14'; // orange

        // Call backend S/R detector (using existing /api/ai/sr-levels endpoint)
        const res = await fetch('/api/ai/sr-levels?style=line&max=6&major=1&circles=1', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ t, h, l, c })
        });

        let payload;
        try {
            payload = await res.json();
        } catch (e) {
            console.error('Bad JSON from /api/ai/sr-levels', e);
            return;
        }

        if (!res.ok || payload.error) {
            console.error('S/R API error:', payload.error || res.status);
            return;
        }

        const prices = Array.isArray(payload.levels) ? payload.levels : [];
        if (!prices.length) {
            // Clear any old auto S/R overlays
            const el = chartState.el;
            const layout = chartState.layout;
            if (!el || !layout) return;

            const shapes = (layout.shapes || []).filter(s => s._generated_by !== 'auto_sr');
            const annotations = (layout.annotations || []).filter(a => a._generated_by !== 'auto_sr');
            layout.shapes = shapes;
            layout.annotations = annotations;
            await Plotly.relayout(el, { shapes, annotations });

            const legendEl = document.getElementById('levels-legend');
            if (legendEl) {
                legendEl.innerHTML = '<div class="text-muted small">No clear support or resistance detected.</div>';
            }
            return;
        }

        const el = chartState.el;
        const layout = chartState.layout;
        if (!el || !layout) return;

        const x0 = t[0];
        const x1 = t[t.length - 1];

        // Sort by distance to current price and cap number of levels
        const MAX_LEVELS = 4;
        let levels = prices.map(price => ({
            price,
            dist: Math.abs(price - currentPrice)
        }));
        levels.sort((a, b) => a.dist - b.dist);
        levels = levels.slice(0, MAX_LEVELS);

        // Strip previous auto S/R shapes + annotations
        const baseShapes = (layout.shapes || []).filter(s => s._generated_by !== 'auto_sr');
        const baseAnnotations = (layout.annotations || []).filter(a => a._generated_by !== 'auto_sr');

        const newShapes = [];
        const newAnnotations = [];

        levels.forEach((lv, idx) => {
            const price = lv.price;
            const isResistance = price > currentPrice;
            const color = isResistance ? resistanceColor : supportColor;
            const typeLabel = isResistance ? 'R' : 'S';

            // Horizontal line across chart
            newShapes.push({
                type: 'line',
                xref: 'x',
                yref: 'y',
                x0,
                x1,
                y0: price,
                y1: price,
                line: {
                    color,
                    width: 3
                },
                _generated_by: 'auto_sr'
            });

            // Right-edge label
            newAnnotations.push({
                x: 1.002,         // just off the right edge
                xref: 'paper',
                y: price,
                yref: 'y',
                text: `${typeLabel}${idx + 1}  $${price.toFixed(2)}`,
                showarrow: false,
                align: 'left',
                bgcolor: 'rgba(255,255,255,0.9)',
                bordercolor: color,
                borderwidth: 1,
                font: { size: 11, color },
                _generated_by: 'auto_sr'
            });
        });

        // Optionally add pivot circle overlays from backend (keep them light)
        if (Array.isArray(payload.pivot_circles)) {
            payload.pivot_circles.forEach(shape => {
                const s = Object.assign({}, shape, { _generated_by: 'auto_sr' });
                newShapes.push(s);
            });
        }

        layout.shapes = [...baseShapes, ...newShapes];
        layout.annotations = [...baseAnnotations, ...newAnnotations];

        await Plotly.relayout(el, {
            shapes: layout.shapes,
            annotations: layout.annotations
        });

        // Update legend under the chart
        const legendEl = document.getElementById('levels-legend');
        if (legendEl) {
            let html = '';

            levels.forEach(lv => {
                const price = lv.price;
                const isResistance = price > currentPrice;
                const typeText = isResistance ? 'Resistance' : 'Support';
                const distancePct = ((price - currentPrice) / currentPrice) * 100;
                const distanceLabel = `${Math.abs(distancePct).toFixed(1)}% ${isResistance ? 'above' : 'below'}`;

                const badgeClass = isResistance
                    ? 'bg-light text-warning'
                    : 'bg-light text-primary';

                html += `
                    <div class="d-flex align-items-center small mb-1">
                        <span class="badge ${badgeClass} me-2">${typeText}</span>
                        <span class="fw-semibold">$${price.toFixed(2)}</span>
                        <span class="text-muted ms-2">(${distanceLabel})</span>
                    </div>
                `;
            });

            legendEl.innerHTML = html;
        }
    } catch (err) {
        console.error('applyAutoSupportResistance error:', err);
    }
}

// Update session information display
function updateSessionInfo(data) {
    if (!data || !data.session) return;
    
    const counts = {
        premarket: 0,
        regular: 0,
        afterhours: 0
    };
    
    data.session.forEach(s => {
        if (counts[s] !== undefined) counts[s]++;
    });
    
    const infoEl = document.getElementById('session-info');
    if (infoEl) {
        const total = counts.premarket + counts.regular + counts.afterhours;
        infoEl.innerHTML = `
            <span class="badge bg-light text-dark me-2">
                <i class="fas fa-sun text-warning"></i> Pre: ${counts.premarket}
            </span>
            <span class="badge bg-primary me-2">
                <i class="fas fa-chart-line"></i> Regular: ${counts.regular}
            </span>
            <span class="badge bg-dark me-2">
                <i class="fas fa-moon text-info"></i> After: ${counts.afterhours}
            </span>
            <span class="badge bg-secondary">
                Total: ${total} bars
            </span>
        `;
    }
}

// Toggle handlers for display options
function setupEnhancedToggleHandlers() {
    const toggles = ['show-premarket', 'show-afterhours', 'hide-closed', 'highlight-extended'];
    
    toggles.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', async () => {
                if (chartState.data.full) {
                    // Update display preferences
                    chartState.display.showPremarket = document.getElementById('show-premarket')?.checked ?? true;
                    chartState.display.showAfterhours = document.getElementById('show-afterhours')?.checked ?? true;
                    chartState.display.hideClosed = document.getElementById('hide-closed')?.checked ?? true;
                    chartState.display.highlightExtended = document.getElementById('highlight-extended')?.checked ?? true;
                    
                    // Rebuild display data
                    const displayData = buildDisplayData(chartState);
                    
                    // Create new traces
                    const traces = createEnhancedTraces(displayData, chartState.display);
                    
                    // Update rangebreaks
                    const rangebreaks = buildEnhancedRangebreaks({
                        showPremarket: chartState.display.showPremarket,
                        showAfterhours: chartState.display.showAfterhours,
                        hideClosed: chartState.display.hideClosed,
                        timeframe: chartState.timeframe
                    });
                    
                    // Update chart
                    await Plotly.react(chartState.el, traces, {
                        ...chartState.layout,
                        xaxis: {
                            ...chartState.layout.xaxis,
                            rangebreaks
                        },
                        showlegend: chartState.display.highlightExtended
                    });
                    
                    // Update session info
                    updateSessionInfo(displayData);
                }
            });
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Setup load button
    const loadBtn = document.getElementById('load-chart');
    if (loadBtn) {
        loadBtn.addEventListener('click', loadEnhancedChart);
    }
    
    // Setup toggle handlers
    setupEnhancedToggleHandlers();
    
    // Setup timeframe change handler
    const timeframeSelect = document.getElementById('chart-timeframe');
    if (timeframeSelect) {
        timeframeSelect.addEventListener('change', () => {
            if (chartState.data.full) {
                loadEnhancedChart();
            }
        });
    }
});

// Export for use in other scripts
window.EnhancedChart = {
    load: loadEnhancedChart,
    getState: () => chartState,
    updateDisplay: (options) => {
        Object.assign(chartState.display, options);
        if (chartState.data.full) {
            loadEnhancedChart();
        }
    }
};


