  function timer_hour(desc) {
      var d = new Date();
      $("#head_datetime").html(desc + d.toLocaleTimeString()) ;
  }

  function linspacer(startValue, stopValue, cardinality, multiplier, adder) {
    var arr = [];
    var currValue = startValue;
    var step = (stopValue - startValue) / (cardinality - 1);
    for (var i = 0; i < cardinality; i++) {
      arr.push(Math.round((currValue + (step * i)) * multiplier + adder));
    }
    return arr;
  }

  function map (num, in_min, in_max, out_min, out_max) {
    return (num - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
  }

  // Returns a single rgb color interpolation between given rgb color
  // based on the factor given; via https://codepen.io/njmcode/pen/axoyD?editors=0010
  function interpolateColor(color1, color2, factor) {
      if (arguments.length < 3) { 
          factor = 0.5; 
      }
      var result = color1.slice();
      for (var i = 0; i < 3; i++) {
          result[i] = Math.round(result[i] + factor * (color2[i] - color1[i]));
      }
      return "rgb("+result[0].toString() + "," + result[1].toString() + "," + result[2].toString() + ")";
  };
  // My function to interpolate between two colors completely, returning an array
  function interpolateColors(color1, color2, steps) {
      var stepFactor = 1 / (steps - 1),
          interpolatedColorArray = [];

      color1 = color1.match(/\d+/g).map(Number);
      color2 = color2.match(/\d+/g).map(Number);

      for(var i = 0; i < steps; i++) {
          interpolatedColorArray.push(interpolateColor(color1, color2, stepFactor * i));
      }
      return interpolatedColorArray;
  }


    function initialize_canvasJS()
  {
    canvasJSchart = new CanvasJS.Chart("canvasJScanvas", {
      axisX: {
        title: "Freq"
      },
      axisY: {
        title: "Amplitude"
      },
      data: [{
        type: "spline",
        name: "{{description}}",
        showInLegend: false,
        dataPoints: []
      }]
    });    
  }
  function draw_canvasJS(fft_data)
  {
    var axis = linspacer(-1, 1, fft_data.length, samp_rate/2.0, tune_freq)
    var max = Math.max.apply(Math, fft_data) + 1
    var min = Math.min.apply(Math, fft_data)
    var dps = []; //dataPoints. 

    for (var i = 0; i < fft_data.length; i++)
      dps.push({
        y: fft_data[i], label: axis[i]
      });

    canvasJSchart.options.data[0].dataPoints = dps;
    canvasJSchart.options.axisY.maximum = max;
    canvasJSchart.options.axisY.minimum = min;
    canvasJSchart.render();
    canvasJSchart.destroy();
    //canvasJSchart = null;
    //dps = null;
  }
  function initialize_chartJS()
  {
    var ctx = document.getElementById("chartJScanvas").getContext('2d');
    chartJSchart = new Chart(ctx, {
        type: 'line',
        fill: false,
        data: {
            labels: [],
            datasets: [{
                label: 'FFT',
                data: [],
                borderColor: 'rgba(0,0,255,0.3)',
            }]
        },
        options: {
            animation: false,
            elements: {
                line: {
                  fill: false
                },
                point: {
                  radius: 0 }
            }
        }
    });
  }
  function draw_chartJS(fft_data)
  { 
    var axis = linspacer(-1, 1, fft_data.length, samp_rate/2.0, tune_freq)
    chartJSchart.data = {
            labels: axis,
            datasets: [{
                label: 'FFT',
                data: fft_data,
                borderColor: 'rgba(0,0,255,0.3)',
            }]
        }
    chartJSchart.update();
  }