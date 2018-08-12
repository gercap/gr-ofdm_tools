$(function() {
    $('tr > td:odd').each(function(index) {
        var scale = [['vPoor', 1], ['poor', 2], ['avg', 3], ['good', 4], ['vGood', 10]];
        var score = $(this).text();
        for (var i = 0; i < scale.length; i++) {
            if (score <= scale[i][1]) {
                $(this).addClass(scale[i][0]);
            }
        }
    });
});