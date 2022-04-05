tracks_num = 0

function bindTrackButtons() {
    $(".button-track-record").click(function () {
        var trackId = $(this).attr('track-id')
        console.log('record track ' + trackId)
        $.ajax({
            url: '/api/track/' + trackId + '/record',
            type: 'post',
            data: {},
            cache: false,
            success: function(data) {
                refreshTrack(trackId);
            },
            error: function (xhr, status, error) {
                showAlert('Error: ' + error, 'danger')
            }
        })
    })

    $(".button-track-play").click(function () {
        var trackId = $(this).attr('track-id')
        console.log('play track ' + trackId)
        $.ajax({
            url: '/api/track/' + trackId + '/play',
            type: 'post',
            data: {},
            cache: false,
            success: function(data) {
                refreshTrack(trackId)
            },
            error: function (xhr, status, error) {
                showAlert('Error: ' + error, 'danger')
            }
        })
    })

    $(".button-track-reset").click(function () {
        var trackId = $(this).attr('track-id')
        console.log('reset track ' + trackId)
        $.ajax({
            url: '/api/track/' + trackId + '/reset',
            type: 'post',
            data: {},
            cache: false,
            success: function(data) {
                refreshTrack(trackId)
            },
            error: function (xhr, status, error) {
                showAlert('Error: ' + error, 'danger')
            }
        })
    })
}

function bindRecorderButtons() {
    $("#btn-save-output").click(function () {
        console.log('record output')
        $.ajax({
            url: '/api/recorder/toggle',
            type: 'post',
            data: {},
            cache: false,
            success: function(data) {
                refreshOutputRecorderStatus()
            },
            error: function (xhr, status, error) {
                showAlert('Error: ' + error, 'danger')
            }
        })
    })
}

function refreshAllStatus() {
    refreshTracks()
    refreshLooperStatus()
    refreshOutputRecorderStatus()
}

function refreshTracks() {
    for (var i = 0; i < tracks_num; i++) {
        refreshTrack(i)
    }
}

function refreshTrack(trackId) {
    $.ajax({
        url: '/api/track/' + trackId,
        type: 'get',
        data: {},
        cache: false,
        success: function(data) {
            var recording = data.recording
            var playing = data.playing
            var nonempty = !data.empty
            updateElementClass("#label-track-"+trackId+"-recording", recording, "bg-danger", "bg-secondary text-decoration-line-through")
            updateElementClass("#label-track-"+trackId+"-playing", playing, "bg-success", "bg-secondary text-decoration-line-through")
            updateElementClass("#label-track-"+trackId+"-nonempty", nonempty, "bg-warning text-dark", "bg-secondary text-decoration-line-through")
        },
        error: function (xhr, status, error) {
            showAlert('Error: ' + error, 'danger')
        }
    })
}

function refreshLooperStatus() {
    $.ajax({
        url: '/api/player',
        type: 'get',
        data: {},
        cache: false,
        success: function(data) {
            $("#looper-status-phase").html(data.phase)
            $("#looper-status-position").html(data.position)
            $("#looper-status-duration").html(data.loop_duration)
        },
        error: function (xhr, status, error) {
            showAlert('Error: ' + error, 'danger')
        }
    })
}

function refreshOutputRecorderStatus() {
    $.ajax({
        url: '/api/recorder',
        type: 'get',
        data: {},
        cache: false,
        success: function(data) {
            $("#recorder-status-saving").html(data.saving.toString())
            $("#recorder-status-duration").html(data.recorded_duration.toString() + 's')
        },
        error: function (xhr, status, error) {
            showAlert('Error: ' + error, 'danger')
        }
    })
}

function updateElementClass(elementId, condition, onClass, offClass) {
    if (condition) {
        $(elementId).addClass(onClass)
        $(elementId).removeClass(offClass)
    } else {
        $(elementId).addClass(offClass)
        $(elementId).removeClass(onClass)
    }
}

function showAlert(message, type) {
    console.log('alert ' + type + ': ' + message)
    var wrapper = document.createElement('div')
    wrapper.innerHTML = '<div class="alert alert-' + type + ' alert-dismissible" role="alert">' + message + '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>'
    document.getElementById('alerts-placeholder').append(wrapper)
}
