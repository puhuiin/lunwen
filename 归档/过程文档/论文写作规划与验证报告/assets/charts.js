// Chart visualizations for the research planning report
(function() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var positive = style.getPropertyValue('--positive').trim();
  var negative = style.getPropertyValue('--negative').trim();
  var warning = style.getPropertyValue('--warning').trim();

  // Chart 1: AS Variation Problem
  var chart1 = document.getElementById('chart-as-variation');
  if (chart1) {
    echarts.init(chart1).setOption({
      title: { text: 'AS指标变异度问题', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: { trigger: 'item', formatter: '{b}: {c} 条 ({d}%)' },
      legend: { bottom: 0, textStyle: { fontSize: 12 } },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        data: [
          { value: 5923, name: '相同值(0.832)', itemStyle: { color: negative } },
          { value: 3658, name: '不同值', itemStyle: { color: positive } }
        ],
        label: { formatter: '{b}\n{d}%', fontSize: 11 }
      }]
    });
  }

  // Chart 2: Regression t-values Comparison
  var chart2 = document.getElementById('chart-tvalues');
  if (chart2) {
    echarts.init(chart2).setOption({
      title: { text: '核心指标回归t值对比（多方法交叉验证）', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { bottom: 0, textStyle: { fontSize: 11 } },
      grid: { left: '8%', right: '5%', bottom: '15%', top: '15%' },
      xAxis: { type: 'category', data: ['AS', 'RG', 'ICI', 'SDI', 'OCI'], axisLabel: { fontSize: 12 } },
      yAxis: { type: 'value', name: 't值', axisLabel: { fontSize: 11 } },
      series: [
        {
          name: '单变量OLS',
          type: 'bar',
          data: [-5.24, -3.67, -3.69, -0.30, -13.45],
          itemStyle: { color: accent }
        },
        {
          name: '多变量OLS',
          type: 'bar',
          data: [-3.32, -4.76, -2.03, 0.49, -13.97],
          itemStyle: { color: accent2 }
        },
        {
          name: '因子调整',
          type: 'bar',
          data: [-2.44, 1.52, 0.66, -5.05, 4.79],
          itemStyle: { color: warning }
        },
        {
          name: '牛市子样本',
          type: 'bar',
          data: [-8.31, -3.09, null, null, null],
          itemStyle: { color: positive }
        }
      ]
    });
  }

  // Chart 3: Data Completeness Heatmap
  var chart3 = document.getElementById('chart-data-quality');
  if (chart3) {
    var variables = ['AS', 'RG', 'ICI', 'SDI', 'OCI', 'delta_AS', 'HML', 'MOM', 'manager_name', 'AS_new', 'manager_tenure', 'log_aum'];
    var missingPct = [0, 0, 0, 0, 0, 4.2, 57.6, 0.2, 66.2, 82.6, 0, 0];
    var completeness = missingPct.map(function(p) { return 100 - p; });
    echarts.init(chart3).setOption({
      title: { text: '面板数据变量完整度（%）', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: { trigger: 'axis', formatter: function(params) { return params[0].name + ': ' + params[0].value + '% 完整 (' + (100-params[0].value) + '% 缺失)'; } },
      grid: { left: '15%', right: '8%', bottom: '10%', top: '15%' },
      xAxis: { type: 'value', max: 100, axisLabel: { fontSize: 11, formatter: '{value}%' } },
      yAxis: { type: 'category', data: variables, axisLabel: { fontSize: 11 } },
      series: [{
        type: 'bar',
        data: completeness.map(function(v) {
          return { value: v, itemStyle: { color: v >= 95 ? positive : (v >= 50 ? warning : negative) } };
        }),
        label: { show: true, position: 'right', formatter: '{c}%', fontSize: 10 }
      }]
    });
  }

  // Chart 4: R-squared Comparison
  var chart4 = document.getElementById('chart-rsquared');
  if (chart4) {
    echarts.init(chart4).setOption({
      title: { text: '模型解释力(R²)对比', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: { trigger: 'axis' },
      grid: { left: '10%', right: '8%', bottom: '15%', top: '15%' },
      xAxis: { type: 'category', data: ['单变量AS', '单变量RG', '单变量OCI', '单变量ICI', '多变量OLS', '因子调整', '牛市子样本', '熊市子样本'], axisLabel: { fontSize: 10, rotate: 30 } },
      yAxis: { type: 'value', name: 'R²', axisLabel: { fontSize: 11 } },
      series: [{
        type: 'bar',
        data: [
          { value: 0.00234, itemStyle: { color: accent } },
          { value: 0.00168, itemStyle: { color: accent } },
          { value: 0.01716, itemStyle: { color: accent } },
          { value: 0.00072, itemStyle: { color: accent } },
          { value: 0.02371, itemStyle: { color: accent2 } },
          { value: 0.00000, itemStyle: { color: negative } },
          { value: 0.00794, itemStyle: { color: positive } },
          { value: 0.00134, itemStyle: { color: warning } }
        ],
        label: { show: true, position: 'top', formatter: '{c}', fontSize: 9 }
      }]
    });
  }

  // Chart 5: Five-Layer Framework
  var chart5 = document.getElementById('chart-framework');
  if (chart5) {
    echarts.init(chart5).setOption({
      title: { text: '五层递进框架：指标→数据→文献映射', left: 'center', textStyle: { fontSize: 14, color: ink } },
      tooltip: { trigger: 'item' },
      series: [{
        type: 'tree',
        data: [{
          name: '基金经理行为画像',
          children: [
            {
              name: 'L1 背景特征',
              children: [
                { name: '从业年限', itemStyle: { color: positive } },
                { name: '管理规模', itemStyle: { color: positive } },
                { name: 'Chevalier(1999)', itemStyle: { color: accent } }
              ]
            },
            {
              name: 'L2 持仓偏离',
              children: [
                { name: 'AS=0.832(问题!)', itemStyle: { color: negative } },
                { name: 'ICI=711(量纲错误!)', itemStyle: { color: negative } },
                { name: 'Cremers(2009)', itemStyle: { color: accent } }
              ]
            },
            {
              name: 'L3 交易行为',
              children: [
                { name: 'RG(均值≈0)', itemStyle: { color: warning } },
                { name: 'delta_AS', itemStyle: { color: positive } },
                { name: 'Kacperczyk(2008)', itemStyle: { color: accent } }
              ]
            },
            {
              name: 'L4 风险应对',
              children: [
                { name: 'SDI=33.4(量纲错误!)', itemStyle: { color: negative } },
                { name: '寇宗来(2020)', itemStyle: { color: accent } }
              ]
            },
            {
              name: 'L5 认知偏差',
              children: [
                { name: 'OCI=0.058', itemStyle: { color: warning } },
                { name: 'Kahneman(1979)', itemStyle: { color: accent } }
              ]
            }
          ]
        }],
        top: '5%', bottom: '5%', left: '15%', right: '15%',
        symbolSize: 8,
        label: { fontSize: 10, color: ink },
        leaves: { label: { fontSize: 10, color: muted } },
        animationDuration: 500
      }]
    });
  }

  // Resize handler
  window.addEventListener('resize', function() {
    document.querySelectorAll('[id^="chart-"]').forEach(function(el) {
      var instance = echarts.getInstanceByDom(el);
      if (instance) instance.resize();
    });
  });
})();
