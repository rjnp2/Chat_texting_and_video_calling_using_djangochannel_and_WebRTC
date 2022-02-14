//Status constants
var SESSION_STATUS = Flashphoner.constants.SESSION_STATUS;
var STREAM_STATUS = Flashphoner.constants.STREAM_STATUS;
var session;
var PRELOADER_URL = "https://github.com/flashphoner/flashphoner_client/raw/wcs_api-2.0/examples/demo/dependencies/media/preloader.mp4";
var conferenceStream;
var publishStream;

//Init Flashphoner API on page load
function init_api() {
    Flashphoner.init({});

    //Connect to WCS server over websockets
    session = Flashphoner.createSession({
        urlServer: "wss://demo.flashphoner.com" //specify the address of your WCS
    }).on(SESSION_STATUS.ESTABLISHED, function(session) {
        console.log("ESTABLISHED");
    });

    joinBtn.onclick = joinBtnClick;
    var remoteVideo = document.getElementById("remoteVideo");
    var localDisplay = document.getElementById("localDisplay");
}

//Detect browser
var Browser = {
    isSafari: function() {
        return /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
    },
}

function joinBtnClick() {
    if (Browser.isSafari()) {
        Flashphoner.playFirstVideo(document.getElementById("localDisplay"), true, PRELOADER_URL).then(function() {
            startStreaming(session);
        });
    } else {
        startStreaming(session);
    }
}

function startStreaming(session) {
    var login = document.getElementById("login").value;
    var streamName = login + "#" + "room1";
    var constraints = {
        audio: true,
        video: true
    };
    
    publishStream = session.createStream({
        name: streamName,
        display: localDisplay,
        receiveVideo: false,
        receiveAudio: false,
        constraints: constraints,
    }).on(STREAM_STATUS.PUBLISHING, function(publishStream) {
        if (Browser.isSafari()) {
            Flashphoner.playFirstVideo(document.getElementById("remoteVideo"), true, PRELOADER_URL).then(function() {
                playStream(session);
            });
        } else {
            playStream(session);
        }
    })
    publishStream.publish();
}

function playStream(session) {
    var login = document.getElementById("login").value;
    var streamName = "room1" + "-" + login + "room1";
    var constraints = {
        audio: true,
        video: true
    };
    conferenceStream = session.createStream({
        name: streamName,
        display: remoteVideo,
        constraints: constraints,

    }).on(STREAM_STATUS.PLAYING, function(stream) {})
    conferenceStream.play();
}