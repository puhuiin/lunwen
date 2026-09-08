(function() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim() || '#1A56DB';
  var accent2 = style.getPropertyValue('--accent2').trim() || '#DC2626';
  var ink = style.getPropertyValue('--ink').trim() || '#1A1A2E';
  var muted = style.getPropertyValue('--muted').trim() || '#6B7280';
  var rule = style.getPropertyValue('--rule').trim() || '#E2E8F0';
  var bg2 = style.getPropertyValue('--bg2').trim() || '#EEF2FF';
  var green = style.getPropertyValue('--green').trim() || '#059669';
  var orange = style.getPropertyValue('--orange').trim() || '#D97706';
  var gold = style.getPropertyValue('--gold').trim() || '#B45309';

  // --- Chart 1: 7种认知偏差指标的研究价值与数据可行性矩阵 ---
  var chart1 = document.getElementById('chart-feasibility');
  if (chart1) {
    var c1 = echarts.init(chart1, null, { renderer: 'svg' });
    c1.setOption({
      title: { text: '认知偏差指标：研究价值 × 数据可行性', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: {
        trigger: 'item',
        appendToBody: true,
        formatter: function(p) {
          return '<b>' + p.data.name + '</b><br/>研究价值: ' + p.data.value[0] + '/5<br/>数据可行性: ' + p.data.value[1] + '/5<br/>优先级: ' + p.data.priority;
        }
      },
      grid: { left: 60, right: 40, top: 60, bottom: 60 },
      xAxis: {
        name: '研究价值',
        nameLocation: 'middle',
        nameGap: 35,
        min: 2, max: 5.5,
        splitLine: { lineStyle: { color: rule, type: 'dashed' } },
        axisLabel: { color: muted },
        axisLine: { lineStyle: { color: rule } }
      },
      yAxis: {
        name: '数据可行性',
        nameLocation: 'middle',
        nameGap: 40,
        min: 2, max: 5.5,
        splitLine: { lineStyle: { color: rule, type: 'dashed' } },
        axisLabel: { color: muted },
        axisLine: { lineStyle: { color: rule } }
      },
      series: [{
        type: 'scatter',
        symbolSize: function(data) { return data.size || 28; },
        label: {
          show: true,
          position: 'right',
          formatter: function(p) { return p.data.name; },
          fontSize: 11,
          color: ink
        },
        itemStyle: {
          color: function(p) {
            var colors = {
              'riskAsym': green,
              'condTO': green,
              'multiOCI': green,
              'DE': orange,
              'LSV': orange,
              'IMC': orange,
              'WD': accent2
            };
            return colors[p.data.id] || accent;
          },
          opacity: 0.75,
          borderColor: 'rgba(255,255,255,0.8)',
          borderWidth: 2
        },
        data: [
          { id: 'riskAsym', name: '风险承担不对称', value: [5.0, 5.0], priority: 'P0', size: 32 },
          { id: 'condTO', name: '条件换手率', value: [4.5, 5.0], priority: 'P0', size: 28 },
          { id: 'multiOCI', name: '多维过度自信', value: [4.0, 5.0], priority: 'P0', size: 28 },
          { id: 'LSV', name: '羊群效应LSV', value: [4.0, 4.0], priority: 'P1', size: 26 },
          { id: 'IMC', name: '行业动量追逐', value: [3.5, 3.5], priority: 'P1', size: 24 },
          { id: 'DE', name: '处置效应DE', value: [5.0, 3.0], priority: 'P1', size: 30 },
          { id: 'WD', name: '窗口粉饰', value: [3.0, 2.5], priority: 'P2', size: 20 }
        ],
        markArea: {
          itemStyle: { color: 'rgba(5, 150, 105, 0.04)' },
          data: [[{ xAxis: 4, yAxis: 4.5 }, { xAxis: 5.5, yAxis: 5.5 }]]
        },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: rule, type: 'dashed' },
          data: [
            { xAxis: 4, label: { show: false } },
            { yAxis: 4, label: { show: false } }
          ]
        }
      }],
      graphic: [
        {
          type: 'text',
          right: 70,
          top: 65,
          style: { text: 'P0 立即可做', fill: green, fontSize: 11, fontWeight: 600 }
        },
        {
          type: 'text',
          left: 60,
          bottom: 55,
          style: { text: 'P2 困难', fill: accent2, fontSize: 11, fontWeight: 600 }
        }
      ]
    });
    window.addEventListener('resize', function() { c1.resize(); });
  }

  // --- Chart 2: 四层框架变量扩充全景图 ---
  var chart2 = document.getElementById('chart-framework');
  if (chart2) {
    var c2 = echarts.init(chart2, null, { renderer: 'svg' });
    c2.setOption({
      title: { text: '各层指标数量：现有 vs 新增', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: { trigger: 'axis', appendToBody: true, axisPointer: { type: 'shadow' } },
      legend: { data: ['现有指标', '新增指标'], top: 30, textStyle: { color: muted } },
      grid: { left: 80, right: 40, top: 70, bottom: 50 },
      xAxis: {
        type: 'category',
        data: ['L1 背景层', 'L2 决策层', 'L3 执行层', 'L4 风险层', 'L5 偏差层'],
        axisLabel: { color: ink, fontWeight: 600, fontSize: 12 },
        axisLine: { lineStyle: { color: rule } }
      },
      yAxis: {
        type: 'value',
        name: '指标数量',
        nameTextStyle: { color: muted },
        splitLine: { lineStyle: { color: rule, type: 'dashed' } },
        axisLabel: { color: muted },
        axisLine: { lineStyle: { color: rule } }
      },
      series: [
        {
          name: '现有指标',
          type: 'bar',
          stack: 'total',
          itemStyle: { color: accent },
          barWidth: '40%',
          label: { show: true, position: 'inside', color: '#fff', fontWeight: 700 },
          data: [4, 2, 3, 2, 0]
        },
        {
          name: '新增指标',
          type: 'bar',
          stack: 'total',
          itemStyle: { color: green },
          label: { show: true, position: 'inside', color: '#fff', fontWeight: 700 },
          data: [2, 2, 2, 3, 3]
        }
      ]
    });
    window.addEventListener('resize', function() { c2.resize(); });
  }

  // --- Chart 3: 新增变量实施优先级排序 ---
  var chart3 = document.getElementById('chart-priority');
  if (chart3) {
    var c3 = echarts.init(chart3, null, { renderer: 'svg' });
    c3.setOption({
      title: { text: '新增变量：研究价值 × 数据可行性 × 优先级', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: {
        trigger: 'item',
        appendToBody: true,
        formatter: function(p) {
          return '<b>' + p.data.name + '</b><br/>层级: ' + p.data.layer + '<br/>研究价值: ' + p.data.value[0] + '/5<br/>可行性: ' + p.data.value[1] + '/5<br/>耗时: ' + p.data.time;
        }
      },
      grid: { left: 60, right: 120, top: 60, bottom: 60 },
      xAxis: {
        name: '研究价值',
        nameLocation: 'middle',
        nameGap: 35,
        min: 2, max: 5.5,
        splitLine: { lineStyle: { color: rule, type: 'dashed' } },
        axisLabel: { color: muted },
        axisLine: { lineStyle: { color: rule } }
      },
      yAxis: {
        name: '数据可行性',
        nameLocation: 'middle',
        nameGap: 40,
        min: 2, max: 5.5,
        splitLine: { lineStyle: { color: rule, type: 'dashed' } },
        axisLabel: { color: muted },
        axisLine: { lineStyle: { color: rule } }
      },
      series: [{
        type: 'scatter',
        symbolSize: function(data) { return data.size || 20; },
        label: {
          show: true,
          position: 'right',
          formatter: function(p) { return p.data.name; },
          fontSize: 10,
          color: ink
        },
        itemStyle: {
          color: function(p) {
            if (p.data.priority === 'P0') return green;
            if (p.data.priority === 'P1') return orange;
            return accent2;
          },
          opacity: 0.75,
          borderColor: 'rgba(255,255,255,0.8)',
          borderWidth: 1.5
        },
        data: [
          { name: 'RiskAsym', value: [5.0, 5.0], layer: 'L4/L5', priority: 'P0', time: '2h', size: 28 },
          { name: 'CondTO', value: [4.5, 5.0], layer: 'L3/L5', priority: 'P0', time: '1h', size: 24 },
          { name: 'Δβ', value: [4.0, 5.0], layer: 'L4', priority: 'P0', time: '2h', size: 22 },
          { name: 'VT', value: [3.5, 5.0], layer: 'L4', priority: 'P0', time: '2h', size: 20 },
          { name: 'HHI', value: [4.0, 5.0], layer: 'L2', priority: 'P0', time: '1h', size: 22 },
          { name: 'TE', value: [3.5, 5.0], layer: 'L2', priority: 'P0', time: '1h', size: 20 },
          { name: 'OCI-3D', value: [4.0, 5.0], layer: 'L3', priority: 'P0', time: '3h', size: 22 },
          { name: 'Holding', value: [3.5, 5.0], layer: 'L3', priority: 'P0', time: '2h', size: 18 },
          { name: 'LSV', value: [4.0, 4.0], layer: 'L5', priority: 'P1', time: '1d', size: 20 },
          { name: 'IMC', value: [3.5, 3.5], layer: 'L5', priority: 'P1', time: '1d', size: 18 },
          { name: 'DE', value: [5.0, 3.0], layer: 'L5', priority: 'P1', time: '2d', size: 24 },
          { name: 'MultiFund', value: [3.0, 4.0], layer: 'L1', priority: 'P1', time: '0.5d', size: 16 }
        ]
      }],
      graphic: [
        { type: 'text', right: 15, top: 60, style: { text: '● P0 立即可做', fill: green, fontSize: 11, fontWeight: 600 } },
        { type: 'text', right: 15, top: 80, style: { text: '● P1 需补数据', fill: orange, fontSize: 11, fontWeight: 600 } },
        { type: 'text', right: 15, top: 100, style: { text: '● P2 困难', fill: accent2, fontSize: 11, fontWeight: 600 } }
      ]
    });
    window.addEventListener('resize', function() { c3.resize(); });
  }

  // --- Chart 4: 5层框架Sankey图 ---
  var chart4 = document.getElementById('chart-sankey');
  if (chart4) {
    var c4 = echarts.init(chart4, null, { renderer: 'svg' });
    c4.setOption({
      title: { text: '完整因果链：是谁 → 持什么 → 怎么调 → 如何控险 → 为何偏', left: 'center', textStyle: { fontSize: 13, color: ink } },
      tooltip: { trigger: 'item', appendToBody: true },
      series: [{
        type: 'sankey',
        layout: 'none',
        emphasis: { focus: 'adjacency' },
        nodeAlign: 'left',
        nodeGap: 8,
        nodeWidth: 18,
        lineStyle: { color: 'gradient', curveness: 0.5, opacity: 0.4 },
        label: { fontSize: 11, color: ink },
        itemStyle: { borderWidth: 0 },
        data: [
          { name: 'L1 经理背景层', itemStyle: { color: accent } },
          { name: '  从业年限', itemStyle: { color: accent + 'CC' } },
          { name: '  学历/院校', itemStyle: { color: accent + 'CC' } },
          { name: '  兼任基金数(新)', itemStyle: { color: green } },
          { name: '  历史最佳排名(新)', itemStyle: { color: green } },

          { name: 'L2 投资决策层', itemStyle: { color: accent } },
          { name: '  AS 主动偏离', itemStyle: { color: accent + 'CC' } },
          { name: '  ICI 行业集中', itemStyle: { color: accent + 'CC' } },
          { name: '  HHI 集中度(新)', itemStyle: { color: green } },
          { name: '  TE 跟踪误差(新)', itemStyle: { color: green } },

          { name: 'L3 交易执行层', itemStyle: { color: accent } },
          { name: '  SDI 风格漂移', itemStyle: { color: accent + 'CC' } },
          { name: '  TO 换手率', itemStyle: { color: accent + 'CC' } },
          { name: '  OCI(3维升级)', itemStyle: { color: green } },
          { name: '  CondTO(新)', itemStyle: { color: green } },

          { name: 'L4 风险管理层', itemStyle: { color: accent } },
          { name: '  ARG 隐形信息', itemStyle: { color: accent + 'CC' } },
          { name: '  Δβ(新)', itemStyle: { color: green } },
          { name: '  RiskAsym(新)', itemStyle: { color: green } },
          { name: '  VT(新)', itemStyle: { color: green } },

          { name: 'L5 认知偏差层(新)', itemStyle: { color: gold } },
          { name: '  DE 处置效应', itemStyle: { color: gold + 'CC' } },
          { name: '  LSV 羊群效应', itemStyle: { color: gold + 'CC' } },
          { name: '  IMC 动量追逐', itemStyle: { color: gold + 'CC' } },

          { name: '业绩 (FF4 α)', itemStyle: { color: accent2 } }
        ],
        links: [
          // L1 to L2
          { source: 'L1 经理背景层', target: '  从业年限', value: 2 },
          { source: 'L1 经理背景层', target: '  学历/院校', value: 2 },
          { source: 'L1 经理背景层', target: '  兼任基金数(新)', value: 1 },
          { source: 'L1 经理背景层', target: '  历史最佳排名(新)', value: 1 },
          { source: '  从业年限', target: 'L2 投资决策层', value: 1 },
          { source: '  学历/院校', target: 'L2 投资决策层', value: 1 },

          // L2 to L3
          { source: 'L2 投资决策层', target: '  AS 主动偏离', value: 2 },
          { source: 'L2 投资决策层', target: '  ICI 行业集中', value: 2 },
          { source: 'L2 投资决策层', target: '  HHI 集中度(新)', value: 1 },
          { source: 'L2 投资决策层', target: '  TE 跟踪误差(新)', value: 1 },
          { source: '  AS 主动偏离', target: 'L3 交易执行层', value: 2 },

          // L3 to L4
          { source: 'L3 交易执行层', target: '  SDI 风格漂移', value: 2 },
          { source: 'L3 交易执行层', target: '  TO 换手率', value: 2 },
          { source: 'L3 交易执行层', target: '  OCI(3维升级)', value: 1 },
          { source: 'L3 交易执行层', target: '  CondTO(新)', value: 1 },
          { source: '  SDI 风格漂移', target: 'L4 风险管理层', value: 2 },

          // L4 to L5/业绩
          { source: 'L4 风险管理层', target: '  ARG 隐形信息', value: 2 },
          { source: 'L4 风险管理层', target: '  Δβ(新)', value: 1 },
          { source: 'L4 风险管理层', target: '  RiskAsym(新)', value: 1 },
          { source: 'L4 风险管理层', target: '  VT(新)', value: 1 },
          { source: '  ARG 隐形信息', target: '业绩 (FF4 α)', value: 3 },
          { source: '  Δβ(新)', target: '业绩 (FF4 α)', value: 1 },

          // L5 to 业绩
          { source: 'L5 认知偏差层(新)', target: '  DE 处置效应', value: 2 },
          { source: 'L5 认知偏差层(新)', target: '  LSV 羊群效应', value: 2 },
          { source: 'L5 认知偏差层(新)', target: '  IMC 动量追逐', value: 1 },
          { source: '  DE 处置效应', target: '业绩 (FF4 α)', value: 2 },
          { source: '  LSV 羊群效应', target: '业绩 (FF4 α)', value: 2 },
          { source: '  IMC 动量追逐', target: '业绩 (FF4 α)', value: 1 },

          // L5 influences L2/L3
          { source: '  DE 处置效应', target: 'L3 交易执行层', value: 1 },
          { source: '  LSV 羊群效应', target: 'L2 投资决策层', value: 1 }
        ]
      }]
    });
    window.addEventListener('resize', function() { c4.resize(); });
  }

})();
