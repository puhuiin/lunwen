// framework_review_report charts
(function() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim() || '#1A56DB';
  var accent2 = style.getPropertyValue('--accent2').trim() || '#DC2626';
  var green = style.getPropertyValue('--green').trim() || '#059669';
  var orange = style.getPropertyValue('--orange').trim() || '#D97706';
  var ink = style.getPropertyValue('--ink').trim() || '#1A1A2E';
  var muted = style.getPropertyValue('--muted').trim() || '#6B7280';
  var rule = style.getPropertyValue('--rule').trim() || '#E2E8F0';

  // Chart 1: UMD修复前后行为指标显著性变化
  var chart1 = document.getElementById('chart-umd-impact');
  if (chart1) {
    echarts.init(chart1).setOption({
      title: { text: 'UMD修复前后行为指标t值变化（M6模型）', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['修复前(错误MOM)', '修复后(真实UMD)'], top: 30 },
      grid: { left: '8%', right: '8%', bottom: '10%', top: 70 },
      xAxis: { type: 'category', data: ['AS', 'SDI', 'ARG', 'OCI'], axisLabel: { fontSize: 13, color: ink } },
      yAxis: { type: 'value', name: 't值', axisLabel: { color: muted }, splitLine: { lineStyle: { color: rule } } },
      series: [
        {
          name: '修复前(错误MOM)',
          type: 'bar',
          data: [-1.40, -3.10, 2.48, -0.45],
          itemStyle: { color: accent2, borderRadius: [4, 4, 0, 0] },
          label: { show: true, position: 'top', fontSize: 11, formatter: function(p) { return p.value > 0 ? '+'+p.value : p.value; } }
        },
        {
          name: '修复后(真实UMD)',
          type: 'bar',
          data: [-3.93, -4.14, -0.13, 5.22],
          itemStyle: { color: accent, borderRadius: [4, 4, 0, 0] },
          label: { show: true, position: 'top', fontSize: 11, formatter: function(p) { return p.value > 0 ? '+'+p.value : p.value; } }
        }
      ],
      markLine: {
        silent: true,
        data: [
          { yAxis: 1.96, lineStyle: { color: green, type: 'dashed' }, label: { formatter: '5%显著', position: 'end', fontSize: 10 } },
          { yAxis: -1.96, lineStyle: { color: green, type: 'dashed' }, label: { formatter: '-5%显著', position: 'end', fontSize: 10 } },
          { yAxis: 2.58, lineStyle: { color: orange, type: 'dashed' }, label: { formatter: '1%显著', position: 'end', fontSize: 10 } },
          { yAxis: -2.58, lineStyle: { color: orange, type: 'dashed' } }
        ]
      }
    });
  }

  // Chart 2: M6模型回归系数
  var chart2 = document.getElementById('chart-m6-coefs');
  if (chart2) {
    echarts.init(chart2).setOption({
      title: { text: 'M6模型（FF4+扩展控制变量）行为指标回归系数', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: function(params) {
        var p = params[0];
        return p.name + '<br/>系数: ' + p.value.toFixed(4) + '<br/>t值: ' + p.data.tval;
      }},
      grid: { left: '10%', right: '8%', bottom: '10%', top: 60 },
      xAxis: { type: 'category', data: ['AS', 'ICI', 'SDI', 'ARG', 'OCI'], axisLabel: { fontSize: 13, color: ink } },
      yAxis: { type: 'value', name: '回归系数', axisLabel: { color: muted }, splitLine: { lineStyle: { color: rule } } },
      series: [{
        type: 'bar',
        data: [
          { value: -0.0359, tval: '-3.93***', itemStyle: { color: accent2 } },
          { value: 0.0105, tval: '0.70', itemStyle: { color: muted } },
          { value: -0.0137, tval: '-4.14***', itemStyle: { color: accent2 } },
          { value: -0.0006, tval: '-0.13', itemStyle: { color: muted } },
          { value: 0.0189, tval: '5.22***', itemStyle: { color: green } }
        ],
        label: { show: true, position: 'top', fontSize: 11,
          formatter: function(p) { return p.data.tval; }
        },
        barWidth: '40%'
      }]
    });
  }

  // Chart 3: 旧框架 vs 新框架对比（雷达图）
  var chart3 = document.getElementById('chart-framework-compare');
  if (chart3) {
    echarts.init(chart3).setOption({
      title: { text: '框架评估对比：旧5层 vs 新4层', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: {},
      legend: { data: ['旧5层框架', '新4层框架'], top: 30, bottom: 0 },
      radar: {
        indicator: [
          { name: '概念独立性', max: 10 },
          { name: '名实相符', max: 10 },
          { name: '逻辑递进', max: 10 },
          { name: '维度完整', max: 10 },
          { name: '理论支撑', max: 10 },
          { name: '可操作性', max: 10 }
        ],
        center: ['50%', '55%'],
        radius: '60%',
        axisName: { color: ink, fontSize: 12 }
      },
      series: [{
        type: 'radar',
        data: [
          {
            value: [4, 3, 5, 6, 7, 8],
            name: '旧5层框架',
            itemStyle: { color: accent2 },
            areaStyle: { color: 'rgba(220, 38, 38, 0.15)' },
            lineStyle: { color: accent2 }
          },
          {
            value: [8, 9, 9, 7, 8, 7],
            name: '新4层框架',
            itemStyle: { color: accent },
            areaStyle: { color: 'rgba(26, 86, 219, 0.15)' },
            lineStyle: { color: accent }
          }
        ]
      }]
    });
  }

  // Chart 4: 创新性评估
  var chart4 = document.getElementById('chart-innovation');
  if (chart4) {
    echarts.init(chart4).setOption({
      title: { text: '创新点评估：当前 vs 提升方向', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['当前水平', '提升后预期'], top: 30 },
      grid: { left: '12%', right: '8%', bottom: '10%', top: 70 },
      xAxis: { type: 'value', name: '创新性评分', max: 10, axisLabel: { color: muted }, splitLine: { lineStyle: { color: rule } } },
      yAxis: { type: 'category', data: ['中国市场系统验证', '非线性效应发现', '条件性效应图谱', '方法论贡献(FF设定)', 'NLP文本分析'], axisLabel: { fontSize: 12, color: ink }, inverse: true },
      series: [
        {
          name: '当前水平',
          type: 'bar',
          data: [6, 4, 3, 5, 0],
          itemStyle: { color: accent2, borderRadius: [0, 4, 4, 0] },
          label: { show: true, position: 'right', fontSize: 11 }
        },
        {
          name: '提升后预期',
          type: 'bar',
          data: [8, 8, 7, 7, 6],
          itemStyle: { color: accent, borderRadius: [0, 4, 4, 0] },
          label: { show: true, position: 'right', fontSize: 11 }
        }
      ]
    });
  }

  // Chart 5: 数据补充优先级
  var chart5 = document.getElementById('chart-data-priority');
  if (chart5) {
    echarts.init(chart5).setOption({
      title: { text: '数据补充优先级与影响评估', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: {
        formatter: function(params) {
          return params.data.name + '<br/>优先级: ' + params.data.priority + '<br/>影响: ' + params.data.impact + '<br/>获取难度: ' + params.data.difficulty;
        }
      },
      grid: { left: '15%', right: '15%', bottom: '12%', top: 60 },
      xAxis: { type: 'value', name: '获取难度(1-10)', max: 10, axisLabel: { color: muted }, splitLine: { lineStyle: { color: rule } } },
      yAxis: { type: 'value', name: '研究影响(1-10)', max: 10, axisLabel: { color: muted }, splitLine: { lineStyle: { color: rule } } },
      series: [{
        type: 'scatter',
        symbolSize: function(data) { return data.size; },
        data: [
          { name: '退市/清盘基金', value: [3, 10, 30], priority: 'P0必须', impact: '消除幸存者偏差', difficulty: 3, size: 30, itemStyle: { color: accent2 } },
          { name: '基金年报文本', value: [7, 9, 28], priority: 'P1高价值', impact: 'NLP情感分析', difficulty: 7, size: 28, itemStyle: { color: orange } },
          { name: '基金beta时序', value: [2, 8, 25], priority: 'P1高价值', impact: '真正风险应对指标', difficulty: 2, size: 25, itemStyle: { color: orange } },
          { name: '基金申赎流量', value: [4, 6, 22], priority: 'P1高价值', impact: '锦标赛替代度量', difficulty: 4, size: 22, itemStyle: { color: orange } },
          { name: '完整持仓数据', value: [9, 7, 24], priority: 'P2理想', impact: '更精确AS/SDI', difficulty: 9, size: 24, itemStyle: { color: green } },
          { name: '投资者情绪指数', value: [5, 5, 18], priority: 'P2理想', impact: '宏观情绪控制', difficulty: 5, size: 18, itemStyle: { color: green } }
        ],
        label: { show: true, formatter: function(p) { return p.data.name; }, position: 'top', fontSize: 11, color: ink }
      }]
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
