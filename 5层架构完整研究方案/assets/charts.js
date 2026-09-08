/* ============================================================
 * 5层架构完整研究方案 — 图表渲染（v2: 数据验证版）
 * 四张图：5层架构总览、四维创新体系、VIF验证、实施时间线
 * ============================================================ */
(function () {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim() || '#1A56DB';
  var accent2 = style.getPropertyValue('--accent2').trim() || '#DC2626';
  var green = style.getPropertyValue('--green').trim() || '#059669';
  var orange = style.getPropertyValue('--orange').trim() || '#D97706';
  var gold = style.getPropertyValue('--gold').trim() || '#B45309';
  var ink = style.getPropertyValue('--ink').trim() || '#1A1A2E';
  var muted = style.getPropertyValue('--muted').trim() || '#6B7280';
  var bg2 = style.getPropertyValue('--bg2').trim() || '#EEF2FF';

  /* ========== 图1：5层架构总览（漏斗式因果链） ========== */
  var chartOverview = echarts.init(document.getElementById('chart-overview'));
  chartOverview.setOption({
    backgroundColor: 'transparent',
    title: {
      text: '5层递进架构：背景 → 决策 → 执行 → 风控 → 偏差',
      left: 'center',
      top: 10,
      textStyle: { fontSize: 14, color: ink, fontWeight: 600 }
    },
    tooltip: {
      trigger: 'item',
      formatter: function (p) {
        return p.data.tooltip || p.name;
      }
    },
    grid: { left: 60, right: 40, top: 50, bottom: 30 },
    xAxis: { type: 'value', max: 100, show: false },
    yAxis: {
      type: 'category',
      data: ['L5 认知偏差层', 'L4 风险管理层', 'L3 交易执行层', 'L2 投资决策层', 'L1 经理背景层'],
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 12, color: ink, fontWeight: 600 }
    },
    series: [
      {
        type: 'bar',
        barWidth: 45,
        data: [
          {
            value: 100,
            itemStyle: { color: gold, borderRadius: [0, 6, 6, 0] },
            tooltip: 'L5 认知偏差层（全部新增·已验证）<br/>RiskAsym · LSV · DE<br/>理论：前景理论 / 羊群效应 / 处置效应<br/>VIF < 1.10 · 间相关性 |r| < 0.08',
            label: { show: true, position: 'right', formatter: 'RiskAsym · LSV · DE  ★已验证', color: gold, fontSize: 11, fontWeight: 600 }
          },
          {
            value: 85,
            itemStyle: { color: accent2, borderRadius: [0, 6, 6, 0] },
            tooltip: 'L4 风险管理层<br/>ARG · return_volatility · Δβ<br/>理论：隐形信息 / 市场择时',
            label: { show: true, position: 'right', formatter: 'ARG · return_vol · Δβ  Δβ新增', color: accent2, fontSize: 11, fontWeight: 600 }
          },
          {
            value: 70,
            itemStyle: { color: orange, borderRadius: [0, 6, 6, 0] },
            tooltip: 'L3 交易执行层<br/>SDI · TO · OCI<br/>理论：风格漂移 / 换手率 / 过度自信',
            label: { show: true, position: 'right', formatter: 'SDI · TO · OCI', color: orange, fontSize: 11, fontWeight: 600 }
          },
          {
            value: 55,
            itemStyle: { color: green, borderRadius: [0, 6, 6, 0] },
            tooltip: 'L2 投资决策层<br/>AS · ICI · HHI<br/>理论：主动偏离 / 行业集中 / 持仓集中',
            label: { show: true, position: 'right', formatter: 'AS · ICI · HHI  HHI新增', color: green, fontSize: 11, fontWeight: 600 }
          },
          {
            value: 40,
            itemStyle: { color: accent, borderRadius: [0, 6, 6, 0] },
            tooltip: 'L1 经理背景层（控制变量）<br/>从业年限 · 学历 · 院校 · 职业背景<br/>理论：Chevalier & Ellison (1999)',
            label: { show: true, position: 'right', formatter: '从业年限 · 学历 · 院校 · 背景', color: accent, fontSize: 11, fontWeight: 600 }
          }
        ]
      },
      {
        type: 'custom',
        renderItem: function (params, api) {
          return {
            type: 'text',
            style: {
              text: '↑ 因果传导 ↑',
              x: params.coordSys.x + 10,
              y: params.coordSys.y + params.coordSys.height / 2,
              fontSize: 11,
              fill: muted,
              rotation: -Math.PI / 2,
              textAlign: 'center'
            }
          };
        },
        data: [0]
      }
    ]
  });

  /* ========== 图2：四维创新体系（雷达图） ========== */
  var chartInnovation = echarts.init(document.getElementById('chart-innovation'));
  chartInnovation.setOption({
    backgroundColor: 'transparent',
    title: {
      text: '四维创新体系',
      left: 'center',
      top: 10,
      textStyle: { fontSize: 14, color: ink, fontWeight: 600 }
    },
    tooltip: {
      trigger: 'item',
      formatter: function (p) {
        var dims = ['框架创新', '数据创新', '机制创新', '实证创新'];
        var html = '<b>' + p.name + '</b><br/>';
        p.value.forEach(function (v, i) {
          html += dims[i] + ': ' + v + '<br/>';
        });
        return html;
      }
    },
    legend: {
      bottom: 5,
      data: ['本研究', '现有文献均值'],
      textStyle: { color: muted, fontSize: 12 }
    },
    radar: {
      indicator: [
        { name: '框架创新\n(独立偏差层)', max: 10 },
        { name: '数据创新\n(三独立数据源)', max: 10 },
        { name: '机制创新\n(中介效应)', max: 10 },
        { name: '实证创新\n(反向处置效应)', max: 10 }
      ],
      center: ['50%', '52%'],
      radius: '62%',
      splitArea: { areaStyle: { color: ['#FFFFFF', bg2] } },
      axisLine: { lineStyle: { color: '#D1D5DB' } },
      splitLine: { lineStyle: { color: '#D1D5DB' } },
      axisName: { color: ink, fontSize: 11, fontWeight: 600 }
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: [9, 9, 9, 8],
            name: '本研究',
            areaStyle: { color: 'rgba(26,86,219,0.20)' },
            lineStyle: { color: accent, width: 2 },
            itemStyle: { color: accent }
          },
          {
            value: [3, 2, 2, 4],
            name: '现有文献均值',
            areaStyle: { color: 'rgba(220,38,38,0.12)' },
            lineStyle: { color: accent2, width: 1.5, type: 'dashed' },
            itemStyle: { color: accent2 }
          }
        ]
      }
    ]
  });

  /* ========== 图3：VIF验证结果（柱状图） ========== */
  var chartVif = echarts.init(document.getElementById('chart-vif'));
  var vifVars = ['ARG', 'return_volatility', 'OCI', 'ICI', 'AS_improved', 'SDI', 'TO_calc', 'lsv', 'industry_hhi', 'risk_asym', 'de'];
  var vifVals = [1.73, 1.47, 1.39, 1.25, 1.25, 1.15, 1.10, 1.09, 1.08, 1.07, 1.06];
  var vifLayers = ['L4', 'L4', 'L3', 'L2', 'L2', 'L3', 'L3', 'L5', 'L2', 'L5', 'L5'];
  var vifColors = vifLayers.map(function(l) {
    return l === 'L5' ? gold : (l === 'L4' ? accent2 : (l === 'L3' ? orange : (l === 'L2' ? green : accent)));
  });

  chartVif.setOption({
    backgroundColor: 'transparent',
    title: {
      text: 'VIF检验结果：所有变量VIF < 1.73，无多重共线性',
      left: 'center',
      top: 10,
      textStyle: { fontSize: 14, color: ink, fontWeight: 600 }
    },
    tooltip: {
      trigger: 'item',
      formatter: function(p) {
        return p.name + '<br/>VIF = ' + p.value + '<br/>层级: ' + vifLayers[p.dataIndex] + '<br/>状态: ✅ 安全 (< 5)';
      }
    },
    grid: { left: 120, right: 60, top: 50, bottom: 40 },
    xAxis: {
      type: 'value',
      name: 'VIF值',
      max: 2.5,
      axisLabel: { color: muted, fontSize: 11 },
      splitLine: { lineStyle: { color: '#E5E7EB' } },
      markLine: {
        silent: true,
        data: [
          { xAxis: 5, lineStyle: { color: '#F59E0B', type: 'dashed', width: 2 }, label: { formatter: '阈值5', color: '#F59E0B' } },
          { xAxis: 10, lineStyle: { color: '#EF4444', type: 'dashed', width: 2 }, label: { formatter: '阈值10', color: '#EF4444' } }
        ]
      }
    },
    yAxis: {
      type: 'category',
      data: vifVars,
      inverse: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: ink, fontSize: 11, fontWeight: 500 }
    },
    series: [
      {
        type: 'bar',
        barWidth: 20,
        data: vifVals.map(function(v, i) {
          return { value: v, itemStyle: { color: vifColors[i], borderRadius: [0, 4, 4, 0] } };
        }),
        label: {
          show: true,
          position: 'right',
          formatter: function(p) { return p.value.toFixed(2); },
          fontSize: 11,
          color: ink,
          fontWeight: 600
        }
      }
    ]
  });

  /* ========== 图4：实施时间线（甘特图） ========== */
  var chartTimeline = echarts.init(document.getElementById('chart-timeline'));
  var phases = [
    { name: '数据计算\n(3个L5指标)', start: 1, dur: 1, color: green, desc: 'RiskAsym/LSV/DE 已完成✓' },
    { name: 'VIF+描述性统计', start: 1, dur: 0.5, color: green, desc: 'VIF<1.73 已验证✓' },
    { name: '核心回归M0-M4', start: 1.5, dur: 1, color: accent, desc: '5个模型 + 聚类稳健SE' },
    { name: '中介效应检验', start: 2.5, dur: 1, color: orange, desc: 'Sobel + Bootstrap' },
    { name: '稳健性检验', start: 3.5, dur: 1.5, color: orange, desc: '安慰剂/牛熊市/FM/多重检验' },
    { name: '非线性检验', start: 5, dur: 1, color: orange, desc: '二次项 + 五分位分组' },
    { name: 'Ch1 绪论+Ch2 文献', start: 5, dur: 2, color: gold, desc: '研究背景+文献综述' },
    { name: 'Ch3 理论框架', start: 6, dur: 2, color: gold, desc: '5层架构+指标计算' },
    { name: 'Ch4 实证分析', start: 7, dur: 2, color: gold, desc: 'M0-M4回归+稳健性' },
    { name: 'Ch5 传导机制', start: 8, dur: 1, color: gold, desc: '中介效应+非线性' },
    { name: 'Ch6 结论+定稿', start: 9, dur: 4, color: gold, desc: '结论+修改+定稿' }
  ];

  chartTimeline.setOption({
    backgroundColor: 'transparent',
    title: {
      text: '实施时间线：数据已完成 → 5天实证 + 9天写作 = 14天',
      left: 'center',
      top: 10,
      textStyle: { fontSize: 14, color: ink, fontWeight: 600 }
    },
    tooltip: {
      trigger: 'item',
      formatter: function (p) {
        var d = phases[p.dataIndex];
        return '<b>' + d.name.replace('\n', ' ') + '</b><br/>' +
          '时间：第' + d.start + '-' + (d.start + d.dur) + '天<br/>' +
          '内容：' + d.desc;
      }
    },
    grid: { left: 160, right: 50, top: 50, bottom: 40 },
    xAxis: {
      type: 'value',
      name: '天数',
      nameLocation: 'middle',
      nameGap: 25,
      min: 0,
      max: 15,
      interval: 1,
      axisLabel: { color: muted, fontSize: 11 },
      splitLine: { lineStyle: { color: '#E5E7EB' } }
    },
    yAxis: {
      type: 'category',
      data: phases.map(function (p) { return p.name; }),
      inverse: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: ink, fontSize: 11, fontWeight: 500 }
    },
    series: [
      {
        type: 'custom',
        renderItem: function (params, api) {
          var cat = api.value(0);
          var start = api.coord([api.value(1), cat]);
          var end = api.coord([api.value(2), cat]);
          var h = api.size([0, 1])[1] * 0.55;
          return {
            type: 'rect',
            shape: { x: start[0], y: start[1] - h / 2, width: end[0] - start[0], height: h, r: 4 },
            style: { fill: phases[cat].color, opacity: 0.85 }
          };
        },
        encode: { x: [1, 2], y: 0 },
        data: phases.map(function (p, i) { return [i, p.start, p.start + p.dur]; })
      }
    ]
  });

  /* ========== 响应式 ========== */
  window.addEventListener('resize', function () {
    chartOverview.resize();
    chartInnovation.resize();
    chartVif.resize();
    chartTimeline.resize();
  });
})();
