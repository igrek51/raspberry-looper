tracks_num = 0

function bindTrackButtons() {
    $(".button-track-record").click(function () {
        var trackId = $(this).attr('track-id')
        ajaxRequest('post', '/api/track/' + trackId + '/record', function(data) {
            refreshTrack(trackId)
        })
    })

    $(".button-track-play").click(function () {
        var trackId = $(this).attr('track-id')
        ajaxRequest('post', '/api/track/' + trackId + '/play', function(data) {
            refreshTrack(trackId)
        })
    })

    $(".button-track-reset").click(function () {
        var trackId = $(this).attr('track-id')
        ajaxRequest('post', '/api/track/' + trackId + '/reset', function(data) {
            refreshTrack(trackId)
        })
    })
}

function bindRecorderButtons() {
    $("#btn-save-output").click(function () {
        ajaxRequest('post', '/api/recorder/toggle', function(data) {
            refreshOutputRecorderStatus()
        })
    })
}

function bindNewTrackButton() {
    $("#btn-add-track").click(function () {
        ajaxRequest('post', '/api/track/add', function(data) {
            location.reload()
        })
    })
}

function refreshTracks() {
    for (var i = 0; i < tracks_num; i++) {
        refreshTrack(i)
    }
}

function refreshTrack(trackId) {
    ajaxRequest('get', '/api/track/' + trackId, function(data) {
        var recording = data.recording
        var playing = data.playing
        var nonempty = !data.empty
        updateElementClass("#label-track-"+trackId+"-recording", recording, "bg-danger", "bg-secondary text-decoration-line-through")
        updateElementClass("#label-track-"+trackId+"-playing", playing, "bg-success", "bg-secondary text-decoration-line-through")
        updateElementClass("#label-track-"+trackId+"-nonempty", nonempty, "bg-warning text-dark", "bg-secondary text-decoration-line-through")
    })
}

function refreshLooperStatus() {
    ajaxRequest('get', '/api/player', function(data) {
        $("#looper-status-phase").html(data.phase)
        $("#looper-status-progress").html(data.progress)
        $("#looper-status-duration").html(data.loop_duration)
    })
}

function refreshOutputRecorderStatus() {
    ajaxRequest('get', '/api/recorder', function(data) {
        $("#recorder-status-saving").html(data.saving.toString())
        $("#recorder-status-duration").html(data.recorded_duration.toString() + 's')
    })
}

function ajaxRequest(type, url, onSuccess) {
    $.ajax({
        url: url,
        type: type,
        data: {},
        cache: false,
        success: function(data) {
            onSuccess(data)
        },
        error: function (xhr, status, error) {
            if (xhr.hasOwnProperty('responseJSON') && xhr.responseJSON.hasOwnProperty('error')) { 
                message = xhr.responseJSON.error;
            } else {
                message = xhr.statusText;
            }
            showAlert('Error: ' + message, 'danger')
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
    $('.alert-dismissible').click(function () {
        $(this).remove()
    })
}
