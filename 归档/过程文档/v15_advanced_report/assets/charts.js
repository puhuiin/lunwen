(function() {
    var style = getComputedStyle(document.documentElement);
    var accent = style.getPropertyValue('--accent').trim();
    var accent2 = style.getPropertyValue('--accent2').trim();
    var ink = style.getPropertyValue('--ink').trim();
    var muted = style.getPropertyValue('--muted').trim();
    var rule = style.getPropertyValue('--rule').trim();
    var bg2 = style.getPropertyValue('--bg2').trim();

    // --- Chart 1: PSM ATT对比 ---
    var chart1 = echarts.init(document.getElementById('chart-psm-att'), null, { renderer: 'svg' });
    chart1.setOption({
        animation: false,
        tooltip: { trigger: 'axis', appendToBody: true, formatter: function(params) {
            var p = params[0];
            return p.name + '<br/>ATT: ' + p.value + '<br/>t值: ' + (p.name === 'ARG' ? '9.01' : p.name === 'OCI' ? '7.61' : '-9.27') + '<br/>p < 0.001';
        }},
        grid: { left: '15%', right: '10%', top: '15%', bottom: '15%' },
        xAxis: { type: 'category', data: ['ARG (高→低)', 'OCI (高→低)', 'SDI (高→低)'], axisLabel: { color: ink, fontSize: 12 }, axisLine: { lineStyle: { color: rule } } },
        yAxis: { type: 'value', name: 'ATT', axisLabel: { color: muted, fontSize: 11 }, axisLine: { lineStyle: { color: rule } }, splitLine: { lineStyle: { color: rule, type: 'dashed' } } },
        series: [{
            type: 'bar',
            data: [
                { value: 0.0052, itemStyle: { color: accent } },
                { value: 0.0040, itemStyle: { color: accent } },
                { value: -0.0050, itemStyle: { color: accent2 } }
            ],
            barWidth: '40%',
            label: { show: true, position: 'top', formatter: function(params) { return params.value > 0 ? '+' + params.value.toFixed(4) : params.value.toFixed(4); }, color: ink, fontSize: 12, fontWeight: 600 },
            markLine: { data: [{ yAxis: 0 }], lineStyle: { color: muted, width: 1 }, symbol: 'none' }
        }]
    });
    window.addEventListener('resize', function() { chart1.resize(); });

    // --- Chart 2: Bootstrap vs Cluster SE ---
    var chart2 = echarts.init(document.getElementById('chart-boot-se'), null, { renderer: 'svg' });
    chart2.setOption({
        animation: false,
        tooltip: { trigger: 'axis', appendToBody: true },
        legend: { data: ['聚类SE', 'Bootstrap SE'], textStyle: { color: muted, fontSize: 12 }, bottom: 5 },
        grid: { left: '12%', right: '8%', top: '12%', bottom: '20%' },
        xAxis: { type: 'category', data: ['AS', 'ICI', 'SDI', 'ARG', 'OCI'], axisLabel: { color: ink, fontSize: 12 }, axisLine: { lineStyle: { color: rule } } },
        yAxis: { type: 'value', name: '标准误', axisLabel: { color: muted, fontSize: 11 }, splitLine: { lineStyle: { color: rule, type: 'dashed' } } },
        series: [
            { name: '聚类SE', type: 'bar', data: [0.0120, 0.0191, 0.0042, 0.0048, 0.0033], barWidth: '25%', itemStyle: { color: accent } },
            { name: 'Bootstrap SE', type: 'bar', data: [0.0119, 0.0190, 0.0040, 0.0047, 0.0032], barWidth: '25%', itemStyle: { color: accent2 } }
        ]
    });
    window.addEventListener('resize', function() { chart2.resize(); });

    // --- Chart 3: 分位数回归系数变化 ---
    var chart3 = echarts.init(document.getElementById('chart-quantile'), null, { renderer: 'svg' });
    chart3.setOption({
        animation: false,
        tooltip: { trigger: 'axis', appendToBody: true },
        legend: { data: ['ARG', 'SDI', 'OCI'], textStyle: { color: muted, fontSize: 12 }, bottom: 5 },
        grid: { left: '12%', right: '8%', top: '12%', bottom: '20%' },
        xAxis: { type: 'category', data: ['Q10', 'Q25', 'Q50', 'Q75', 'Q90'], axisLabel: { color: ink, fontSize: 12 }, axisLine: { lineStyle: { color: rule } } },
        yAxis: { type: 'value', name: '系数', axisLabel: { color: muted, fontSize: 11 }, splitLine: { lineStyle: { color: rule, type: 'dashed' } } },
        series: [
            { name: 'ARG', type: 'line', data: [0.0016, 0.0121, 0.0162, 0.0181, 0.0221], smooth: true, itemStyle: { color: accent }, lineStyle: { width: 2.5 }, symbolSize: 8 },
            { name: 'SDI', type: 'line', data: [-0.0056, -0.0162, -0.0329, -0.0353, -0.0269], smooth: true, itemStyle: { color: accent2 }, lineStyle: { width: 2.5 }, symbolSize: 8 },
            { name: 'OCI', type: 'line', data: [-0.0046, -0.0117, -0.0021, 0.0024, 0.0061], smooth: true, itemStyle: { color: muted }, lineStyle: { width: 2.5 }, symbolSize: 8 }
        ]
    });
    window.addEventListener('resize', function() { chart3.resize(); });

    // --- Chart 4: PS分组业绩对比 ---
    var chart4 = echarts.init(document.getElementById('chart-ps-group'), null, { renderer: 'svg' });
    chart4.setOption({
        animation: false,
        tooltip: { trigger: 'axis', appendToBody: true },
        grid: { left: '15%', right: '10%', top: '12%', bottom: '15%' },
        xAxis: { type: 'category', data: ['Q1(低PS)', 'Q2', 'Q3', 'Q4', 'Q5(高PS)'], axisLabel: { color: ink, fontSize: 12 }, axisLine: { lineStyle: { color: rule } } },
        yAxis: { type: 'value', name: '平均超额收益', axisLabel: { color: muted, fontSize: 11 }, splitLine: { lineStyle: { color: rule, type: 'dashed' } } },
        series: [{
            type: 'bar',
            data: [
                { value: 0.0464, itemStyle: { color: accent } },
                { value: 0.0432, itemStyle: { color: accent + 'cc' } },
                { value: 0.0384, itemStyle: { color: accent + '99' } },
                { value: 0.0307, itemStyle: { color: accent2 + '99' } },
                { value: 0.0166, itemStyle: { color: accent2 } }
            ],
            barWidth: '50%',
            label: { show: true, position: 'top', formatter: '{c}', color: ink, fontSize: 11 },
            markLine: { data: [{ type: 'average', name: '均值' }], lineStyle: { color: muted, type: 'dashed' }, label: { formatter: '均值: {c}', color: muted } }
        }]
    });
    window.addEventListener('resize', function() { chart4.resize(); });

    // --- Chart 5: 交互效应热力图 ---
    var chart5 = echarts.init(document.getElementById('chart-interaction'), null, { renderer: 'svg' });
    var interactionData = [
        [0, 0, -0.030], // AS, 熊市
        [0, 1, 0.000],  // AS, 牛市(净效应=-0.030+0.030)
        [1, 0, 0.013],  // ICI, 熊市
        [1, 1, -0.011], // ICI, 牛市
        [2, 0, -0.008], // SDI, 熊市
        [2, 1, -0.016], // SDI, 牛市
        [3, 0, 0.013],  // ARG, 熊市
        [3, 1, 0.017],  // ARG, 牛市
        [4, 0, 0.014],  // OCI, 熊市
        [4, 1, -0.016]  // OCI, 牛市
    ];
    chart5.setOption({
        animation: false,
        tooltip: { appendToBody: true, formatter: function(p) {
            var vars = ['AS', 'ICI', 'SDI', 'ARG', 'OCI'];
            var mkts = ['熊市', '牛市'];
            return vars[p.value[0]] + ' × ' + mkts[p.value[1]] + '<br/>净效应: ' + p.value[2].toFixed(4);
        }},
        grid: { left: '15%', right: '15%', top: '8%', bottom: '15%' },
        xAxis: { type: 'category', data: ['熊市', '牛市'], axisLabel: { color: ink, fontSize: 12 }, axisLine: { lineStyle: { color: rule } } },
        yAxis: { type: 'category', data: ['AS', 'ICI', 'SDI', 'ARG', 'OCI'], axisLabel: { color: ink, fontSize: 12 }, axisLine: { lineStyle: { color: rule } } },
        visualMap: { min: -0.035, max: 0.020, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, textStyle: { color: muted, fontSize: 11 }, inRange: { color: [accent2, bg2, accent] } },
        series: [{
            type: 'heatmap',
            data: interactionData,
            label: { show: true, formatter: function(p) { return p.value[2].toFixed(4); }, color: ink, fontSize: 11 },
            emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
        }]
    });
    window.addEventListener('resize', function() { chart5.resize(); });

    // --- Chart 6: 中介效应路径 ---
    var chart6 = echarts.init(document.getElementById('chart-mediation'), null, { renderer: 'svg' });
    chart6.setOption({
        animation: false,
        tooltip: { show: false },
        grid: { left: '5%', right: '5%', top: '5%', bottom: '5%' },
        xAxis: { show: false, min: 0, max: 10 },
        yAxis: { show: false, min: 0, max: 10 },
        series: [
            // SDI path
            { type: 'graph', layout: 'none', symbolSize: 40,
                data: [
                    { name: 'SDI', x: 100, y: 200, symbolSize: 50, itemStyle: { color: accent2 }, label: { show: true, color: '#fff', fontSize: 11, fontWeight: 600 } },
                    { name: '波动率', x: 300, y: 100, symbolSize: 45, itemStyle: { color: accent }, label: { show: true, color: '#fff', fontSize: 10 } },
                    { name: 'FF4收益', x: 500, y: 200, symbolSize: 50, itemStyle: { color: accent }, label: { show: true, color: '#fff', fontSize: 10, fontWeight: 600 } }
                ],
                links: [
                    { source: 'SDI', target: '波动率', label: { show: true, formatter: 'a=0***', color: muted, fontSize: 10 }, lineStyle: { color: accent2, width: 2, curveness: 0 } },
                    { source: '波动率', target: 'FF4收益', label: { show: true, formatter: 'b=0.038***', color: muted, fontSize: 10 }, lineStyle: { color: accent, width: 2, curveness: 0 } },
                    { source: 'SDI', target: 'FF4收益', label: { show: true, formatter: 'c\'=-0.098***\nSobel z=3.01***', color: ink, fontSize: 9, fontWeight: 600 }, lineStyle: { color: muted, width: 1.5, type: 'dashed', curveness: 0.2 } }
                ],
                lineStyle: { opacity: 0.7 }
            }
        ]
    });
    window.addEventListener('resize', function() { chart6.resize(); });

    // --- Chart 7: 非线性效应 ---
    var chart7 = echarts.init(document.getElementById('chart-nonlinear'), null, { renderer: 'svg' });
    chart7.setOption({
        animation: false,
        tooltip: { trigger: 'axis', appendToBody: true },
        legend: { data: ['AS (倒U型)', 'OCI (倒U型)'], textStyle: { color: muted, fontSize: 12 }, bottom: 5 },
        grid: { left: '12%', right: '8%', top: '12%', bottom: '20%' },
        xAxis: { type: 'value', name: '标准化变量值', axisLabel: { color: muted, fontSize: 11 }, axisLine: { lineStyle: { color: rule } } },
        yAxis: { type: 'value', name: '预测FF4收益', axisLabel: { color: muted, fontSize: 11 }, splitLine: { lineStyle: { color: rule, type: 'dashed' } } },
        series: [
            { name: 'AS (倒U型)', type: 'line', data: (function() { var d = []; for (var i = -3; i <= 3; i += 0.1) { d.push([i, 0.4413 * i - 0.0174 * i * i]); } return d; })(), smooth: true, showSymbol: false, itemStyle: { color: accent }, lineStyle: { width: 2.5 } },
            { name: 'OCI (倒U型)', type: 'line', data: (function() { var d = []; for (var i = -3; i <= 3; i += 0.1) { d.push([i, 0.0468 * i - 0.0043 * i * i]); } return d; })(), smooth: true, showSymbol: false, itemStyle: { color: accent2 }, lineStyle: { width: 2.5 } }
        ]
    });
    window.addEventListener('resize', function() { chart7.resize(); });
})();
