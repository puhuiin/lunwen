// framework_optimization_report charts
(function() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim() || '#1A56DB';
  var accent2 = style.getPropertyValue('--accent2').trim() || '#DC2626';
  var green = style.getPropertyValue('--green').trim() || '#059669';
  var orange = style.getPropertyValue('--orange').trim() || '#D97706';
  var ink = style.getPropertyValue('--ink').trim() || '#1A1A2E';
  var muted = style.getPropertyValue('--muted').trim() || '#6B7280';
  var rule = style.getPropertyValue('--rule').trim() || '#E2E8F0';

  // Chart 1: 4层画像框架（Sankey图展示因果链）
  var chart1 = document.getElementById('chart-framework');
  if (chart1) {
    echarts.init(chart1).setOption({
      title: { text: '4层画像框架：经理是谁 → 做了什么 → 怎么做 → 结果', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: { trigger: 'item' },
      series: [{
        type: 'sankey',
        top: 60,
        bottom: 20,
        nodeWidth: 20,
        nodeGap: 12,
        layoutIterations: 32,
        emphasis: { focus: 'adjacency' },
        data: [
          { name: 'L1 经理背景层\n(控制层)', itemStyle: { color: accent2 } },
          { name: '从业年限', itemStyle: { color: '#FCA5A5' } },
          { name: '学历层次', itemStyle: { color: '#FCA5A5' } },
          { name: '毕业院校', itemStyle: { color: '#FCA5A5' } },
          { name: '职业背景', itemStyle: { color: '#FCA5A5' } },

          { name: 'L2 投资决策层\n(持有什么)', itemStyle: { color: accent } },
          { name: 'AS 主动偏离', itemStyle: { color: '#93C5FD' } },
          { name: 'ICI 行业集中', itemStyle: { color: '#93C5FD' } },

          { name: 'L3 交易执行层\n(怎么调仓)', itemStyle: { color: green } },
          { name: 'SDI 风格漂移', itemStyle: { color: '#86EFAC' } },
          { name: 'TO 换手率', itemStyle: { color: '#86EFAC' } },
          { name: 'OCI 过度自信', itemStyle: { color: '#86EFAC' } },

          { name: 'L4 风险管理层\n(如何控险)', itemStyle: { color: orange } },
          { name: 'ARG 隐形交易', itemStyle: { color: '#FCD34D' } },
          { name: '波动率', itemStyle: { color: '#FCD34D' } },

          { name: '基金未来业绩\n(FF4 alpha)', itemStyle: { color: ink } }
        ],
        links: [
          // L1 indicators to L1 layer
          { source: '从业年限', target: 'L1 经理背景层\n(控制层)', value: 3 },
          { source: '学历层次', target: 'L1 经理背景层\n(控制层)', value: 3 },
          { source: '毕业院校', target: 'L1 经理背景层\n(控制层)', value: 3 },
          { source: '职业背景', target: 'L1 经理背景层\n(控制层)', value: 3 },

          // L2 indicators to L2 layer
          { source: 'AS 主动偏离', target: 'L2 投资决策层\n(持有什么)', value: 4 },
          { source: 'ICI 行业集中', target: 'L2 投资决策层\n(持有什么)', value: 4 },

          // L3 indicators to L3 layer
          { source: 'SDI 风格漂移', target: 'L3 交易执行层\n(怎么调仓)', value: 4 },
          { source: 'TO 换手率', target: 'L3 交易执行层\n(怎么调仓)', value: 4 },
          { source: 'OCI 过度自信', target: 'L3 交易执行层\n(怎么调仓)', value: 4 },

          // L4 indicators to L4 layer
          { source: 'ARG 隐形交易', target: 'L4 风险管理层\n(如何控险)', value: 4 },
          { source: '波动率', target: 'L4 风险管理层\n(如何控险)', value: 4 },

          // Layers to outcome
          { source: 'L1 经理背景层\n(控制层)', target: '基金未来业绩\n(FF4 alpha)', value: 2 },
          { source: 'L2 投资决策层\n(持有什么)', target: '基金未来业绩\n(FF4 alpha)', value: 5 },
          { source: 'L3 交易执行层\n(怎么调仓)', target: '基金未来业绩\n(FF4 alpha)', value: 5 },
          { source: 'L4 风险管理层\n(如何控险)', target: '基金未来业绩\n(FF4 alpha)', value: 4 }
        ],
        label: { fontSize: 11, color: ink },
        lineStyle: { color: 'gradient', curveness: 0.5, opacity: 0.4 }
      }]
    });
  }

  // Chart 2: NLP定位图（柱状图展示核心vs增强）
  var chart2 = document.getElementById('chart-nlp-position');
  if (chart2) {
    echarts.init(chart2).setOption({
      title: { text: '研究内容优先级：核心实证 vs 可选增强', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['对核心问题的贡献度', '时间成本(周)'], top: 30 },
      grid: { left: '12%', right: '8%', bottom: '10%', top: 70 },
      xAxis: {
        type: 'category',
        data: ['L1背景控制', 'L2决策层回归', 'L3执行层回归', 'L4风险层回归', '稳健性检验', '五分位分析', '退市基金补充', 'NLP文本分析(可选)'],
        axisLabel: { fontSize: 11, color: ink, rotate: 20 }
      },
      yAxis: [
        { type: 'value', name: '贡献度', max: 10, axisLabel: { color: muted }, splitLine: { lineStyle: { color: rule } } },
        { type: 'value', name: '时间(周)', max: 5, axisLabel: { color: muted }, splitLine: { show: false } }
      ],
      series: [
        {
          name: '对核心问题的贡献度',
          type: 'bar',
          data: [3, 9, 9, 8, 7, 6, 5, 2],
          itemStyle: {
            color: function(params) {
              return params.dataIndex < 6 ? accent : (params.dataIndex === 6 ? orange : muted);
            },
            borderRadius: [4, 4, 0, 0]
          },
          label: { show: true, position: 'top', fontSize: 11 }
        },
        {
          name: '时间成本(周)',
          type: 'line',
          yAxisIndex: 1,
          data: [0.5, 0.5, 0.5, 0.5, 1, 0.5, 1, 3],
          itemStyle: { color: accent2 },
          lineStyle: { color: accent2, width: 2 },
          label: { show: true, fontSize: 11, color: accent2 }
        }
      ]
    });
  }

  // Chart 3: R²分解分析（堆叠柱状图）
  var chart3 = document.getElementById('chart-r2-decomp');
  if (chart3) {
    echarts.init(chart3).setOption({
      title: { text: '各层级对业绩解释力的预期分解（R²贡献）', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: function(params) {
        var total = 0;
        params.forEach(function(p) { total += p.value; });
        var html = '模型R² = ' + total.toFixed(3) + '<br/>';
        params.forEach(function(p) {
          html += p.marker + p.seriesName + ': ' + p.value.toFixed(3) + ' (' + (p.value/total*100).toFixed(1) + '%)<br/>';
        });
        return html;
      }},
      legend: { top: 30, data: ['L1背景层', 'L2决策层', 'L3执行层', 'L4风险层', '控制变量'] },
      grid: { left: '10%', right: '8%', bottom: '12%', top: 70 },
      xAxis: {
        type: 'category',
        data: ['仅L1背景', '仅L2-L4行为', 'L1+L2-L4全模型', 'L1+L2-L4+控制变量'],
        axisLabel: { fontSize: 12, color: ink, rotate: 15 }
      },
      yAxis: { type: 'value', name: 'R²', max: 0.3, axisLabel: { color: muted }, splitLine: { lineStyle: { color: rule } } },
      series: [
        { name: 'L1背景层', type: 'bar', stack: 'total', data: [0.015, 0, 0.015, 0.012], itemStyle: { color: accent2 }, barWidth: '40%' },
        { name: 'L2决策层', type: 'bar', stack: 'total', data: [0, 0.060, 0.055, 0.048], itemStyle: { color: accent } },
        { name: 'L3执行层', type: 'bar', stack: 'total', data: [0, 0.070, 0.065, 0.058], itemStyle: { color: green } },
        { name: 'L4风险层', type: 'bar', stack: 'total', data: [0, 0.050, 0.045, 0.040], itemStyle: { color: orange } },
        { name: '控制变量', type: 'bar', stack: 'total', data: [0, 0, 0, 0.065], itemStyle: { color: muted } }
      ]
    });
  }

  // Responsive resize
  window.addEventListener('resize', function() {
    document.querySelectorAll('[id^="chart-"]').forEach(function(el) {
      var instance = echarts.getInstanceByDom(el);
      if (instance) instance.resize();
    });
  });
})();
