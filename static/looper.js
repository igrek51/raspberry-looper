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

    $(".button-track-active").click(function () {
        var trackId = $(this).attr('track-id')
        ajaxRequest('post', '/api/track/' + trackId + '/active', function(data) {
            refreshTracks()
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
        var active = data.active
        updateElementClass("#label-track-"+trackId+"-recording", recording, "bg-danger", "bg-secondary text-decoration-line-through")
        updateElementClass("#label-track-"+trackId+"-playing", playing, "bg-success", "bg-secondary text-decoration-line-through")
        updateElementClass("#label-track-"+trackId+"-nonempty", nonempty, "bg-warning text-dark", "bg-secondary text-decoration-line-through")
        updateElementClass("#label-track-"+trackId+"-active", active, "bg-info text-dark", "bg-secondary text-decoration-line-through")
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
        $("#recorder-status-phase").html(data.phase)
        $("#recorder-status-duration").html(data.recorded_duration.toString() + 's')
    })
}

function refreshInputVolume() {
    ajaxRequest('get', '/api/volume/input', function(data) {
        $("#volume-input-volume").html(data.volume.toString())
        slider = document.getElementById('slider-input-volume')
        slider.noUiSlider.set(data.volume)
        updateElementClass("#label-volume-input-muted", data.muted, "bg-danger", "bg-secondary text-decoration-line-through")
    })
}

function refreshOutputVolume() {
    ajaxRequest('get', '/api/volume/output', function(data) {
        $("#volume-output-volume").html(data.volume.toString())
        slider = document.getElementById('slider-output-volume')
        slider.noUiSlider.set(data.volume)
        updateElementClass("#label-volume-output-muted", data.muted, "bg-danger", "bg-secondary text-decoration-line-through")
    })
}

function refreshTrackVolumes() {
    for (var i = 0; i < tracks_num; i++) {
        refreshTrackVolume(i)
    }
}

function refreshTrackVolume(trackId) {
    ajaxRequest('get', `/api/volume/track/${trackId}`, function(data) {
        $(`#label-track-${trackId}-volume`).html(data.volume.toString())
        slider = document.getElementById(`slider-track-${trackId}-volume`)
        slider.noUiSlider.set(data.volume)
    })
    ajaxRequest('get', `/api/volume/track/${trackId}/loudness`, function(data) {
        $(`#label-track-${trackId}-loudness`).html(data.loudness.toString())
    })
}


function setupVolumeSlider(sliderId, buttonSetId, buttonM1Id, buttonP1Id, textInputId, onVolumeSet) {
    $("#"+buttonSetId).click(function () {
        volume = $('#'+textInputId).val()
        onVolumeSet(volume)
    })
    var slider = document.getElementById(sliderId)
    noUiSlider.create(slider, {
        start: 0,
        connect: 'lower',
        range: {
            'min': -50,
            'max': 50
        },
        tooltips: true,
        pips: {mode: 'count', values: 5},
        keyboardSupport: true,
        keyboardDefaultStep: 100,
    })
    slider.noUiSlider.on('update', function (values, handle) {
        document.getElementById(textInputId).value = values[handle]
    })
    $("#"+buttonM1Id).click(function () {
        before = parseFloat(slider.noUiSlider.get())
        slider.noUiSlider.set(before - 1)
    })
    $("#"+buttonP1Id).click(function () {
        before = parseFloat(slider.noUiSlider.get())
        slider.noUiSlider.set(before + 1)
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
                message = xhr.responseJSON.error
            } else {
                message = xhr.statusText
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
