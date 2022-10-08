const BASE_URL = document.location.origin;
const MJPEG_URL = "http://192.168.4.1:8080/?action=stream";
const SOI = new Uint8Array([0xff, 0xd8]);
const CONTENT_LENGTH = 'Content-Length';
const TYPE_JPEG = 'image/jpeg';
let controller;
let reader;
let headers = '';
let contentLength = -1;
let imageBuffer = null;
let imageBlob = null;
let bytesCounter = 0;
let frames = 0;

function fetchTelemtry() {
	let info_url = `${BASE_URL}/info`;
	console.log(info_url);
	var time1 = Date.now();
	fetch(info_url).then(function(response) {
		setTimeout(fetchTelemtry(), 1000);
		return response.json();
	}).then(function(infoJson) {
		let data = JSON.stringify(infoJson);
		console.log(infoJson);
		var battery_label = document.getElementById("battery");
		var gyro_label = document.getElementById("gyro");
		var gyro_label_y = document.getElementById("gyroy");
		battery_label.value = infoJson['voltage'];
		gyro_label.value = "x= " + infoJson['gyro_x'];
		gyro_label_y.value =  " y = " + infoJson['gyro_z'];
		var time2 = Date.now();
		console.log(time2 - time1);
		
	});
}

fetchTelemtry();

setInterval(() => {
	document.getElementById('fps').textContent = frames + ' fps';
	frames = 0;
}, 1000);
const getContentLength = headers => {
	return headers.split('\n')
		.find(header => header.startsWith(CONTENT_LENGTH))
		.split(':')[1];
};
const readData = () => {
	reader.read().then(({
			done, value
		}) => {
			if (done) return;
			for (let index = 0; index < value.length; index++) {
				if (value[index] === SOI[0] && value[index + 1] === SOI[1]) {
					contentLength = getContentLength(headers);
					imageBuffer = new Uint8Array(new ArrayBuffer(contentLength));
				}
				if (contentLength <= 0) {
					headers += String.fromCharCode(value[index]);
				} else if (bytesCounter < contentLength) {
					imageBuffer[bytesCounter++] = value[index];
				} else {
					imageBlob = URL.createObjectURL(new Blob([imageBuffer], {
						type: TYPE_JPEG
					}));
					document.getElementById('view').src = imageBlob;
					frames++;
					contentLength = 0;
					bytesCounter = 0;
					headers = '';
				}
			}
			readData();
		})
		.catch(error => {
			console.error(error);
		});
};

function startStream() {
	controller = new AbortController();
	fetch(MJPEG_URL, {
			signal: controller.signal
		})
		.then(response => {
			if (!response.ok) throw Error(response.statusText);
			reader = response.body.getReader();
			readData();
		})
		.catch(error => {
			console.error(error);
		});
}

function stopStream() {
	controller.abort();
}

var isStreamStart = false;

const startStopButton = document.getElementById('start-stop');
const startRunButton = document.getElementById('start-stop-run');

startStopButton.addEventListener('click', event => {
	if (isStreamStart == false) {
		isStreamStart = true;
		startStopButton.style.backgroundImage = "url(static/img/stop.svg)";	
		startStream();		
	} else {
		isStreamStart = false;
		startStopButton.style.backgroundImage = "url(static/img/play.png)";	
		stopStream();			
	}
});

/*
startRunButton.addEventListener('click', event => {
	isStreamStart = false;
	document.getElementById("start-stop").style.display = "none";
	document.getElementById("start-stop-run").style.display = "block";
	stopStream();
}) */

document.getElementById('get-image').addEventListener('click', (event) => {
		let a = document.createElement('a');
		a.href = BASE_URL+'/snapshot';
		a.download = new Date().toLocaleString() + '.jpg';
		a.click();
		//window.open(BASE_URL + '/snapshot');
	   //fetch(BASE_URL+'/snapshot');
	});
document.addEventListener('DOMContentLoaded', function() {
	function b(B) {
		let C;
		switch (B.type) {
			case 'checkbox':
				C = B.checked ? 1 : 0;
				break;
			case 'range':
			case 'select-one':
				C = B.value;
				break;
			case 'button':
			case 'submit':
				C = '1';
				break;
			default:
				return;
		}
		const D = `${c}/control?var=${B.id}&val=${C}`;
		fetch(D).then(E => {
			console.log(`request to ${D} finished, status: ${E.status}`)
		})
	}
	var c = document.location.origin;
	const e = B => {
			B.classList.add('hidden')
		},
		f = B => {
			B.classList.remove('hidden')
		},
		g = B => {
			B.classList.add('disabled'), B.disabled = !0
		},
		h = B => {
			B.classList.remove('disabled'), B.disabled = !1
		},
		i = (B, C, D) => {
			D = !(null != D) || D;
			let E;
			'checkbox' === B.type ? (E = B.checked, C = !!C, B.checked = C) : (E = B.value, B.value = C), D && E !== C ? b(B) : !D && ('aec' === B.id ? C ? e(v) : f(v) : 'agc' === B.id ? C ? (f(t), e(s)) : (e(t), f(s)) : 'awb_gain' === B.id ? C ? f(x) : e(x) : 'face_recognize' === B.id && (C ? h(n) : g(n)))
		};
	document.querySelectorAll('.close').forEach(B => {
		B.onclick = () => {
			e(B.parentNode)
		}
	}), fetch(`${c}/status`).then(function(B) {
		return B.json()
	}).then(function(B) {
		document.querySelectorAll('.default-action').forEach(C => {
			i(C, B[C.id], !1)
		})
	});
	const j = document.getElementById('stream'),
		k = document.getElementById('stream-container'),
		l = document.getElementById('get-still'),
		m = document.getElementById('toggle-stream'),
		n = document.getElementById('face_enroll'),
		o = document.getElementById('close-stream'),
		p = () => {
			window.stop(), m.innerHTML = 'Start Stream'
		},
		q = () => {
			j.src = `${c+':81'}/stream`, f(k), m.innerHTML = 'Stop Stream'
		};
	l.onclick = () => {
		p(), j.src = `${c}/capture?_cb=${Date.now()}`, f(k)
	}, o.onclick = () => {
		p(), e(k)
	}, m.onclick = () => {
		const B = 'Stop Stream' === m.innerHTML;
		B ? p() : q()
	}, n.onclick = () => {
		b(n)
	}, document.querySelectorAll('.default-action').forEach(B => {
		B.onchange = () => b(B)
	});
	const r = document.getElementById('agc'),
		s = document.getElementById('agc_gain-group'),
		t = document.getElementById('gainceiling-group');
	r.onchange = () => {
		b(r), r.checked ? (f(t), e(s)) : (e(t), f(s))
	};
	const u = document.getElementById('aec'),
		v = document.getElementById('aec_value-group');
	u.onchange = () => {
		b(u), u.checked ? e(v) : f(v)
	};
	const w = document.getElementById('awb_gain'),
		x = document.getElementById('wb_mode-group');
	w.onchange = () => {
		b(w), w.checked ? f(x) : e(x)
	};
	const y = document.getElementById('face_detect'),
		z = document.getElementById('face_recognize'),
		A = document.getElementById('framesize');
	A.onchange = () => {
		b(A), 5 < A.value && (i(y, !1), i(z, !1))
	}, y.onchange = () => {
		return 5 < A.value ? (alert('Please select CIF or lower resolution before enabling this feature!'), void i(y, !1)) : void(b(y), !y.checked && (g(n), i(z, !1)))
	}, z.onchange = () => {
		return 5 < A.value ? (alert('Please select CIF or lower resolution before enabling this feature!'), void i(z, !1)) : void(b(z), z.checked ? (h(n), i(y, !0)) : g(n))
	}
});


document.onkeydown =  keyDownEvent;
document.onkeyup = keyUpEvent;
var keyIsPressed = false;

function keyDownEvent(e) {

    e = e || window.event;

	if (!keyIsPressed)
	{
		keyIsPressed = true;
    if (e.keyCode == '38') {
        fetch(document.location.origin+'/control?var=car&val=1'); // forward
    }
	else if (e.keyCode == '39') {
		fetch(document.location.origin+'/control?var=car&val=4'); // right 
	 }

	else if (e.keyCode == '40') {
        fetch(document.location.origin+'/control?var=car&val=5'); // backward
    }
    else if (e.keyCode == '37') //left
	{
		fetch(document.location.origin+'/control?var=car&val=2');
    }
    }
}


function keyUpEvent(e) {

    e = e || window.event;

    if (e.keyCode == '38' || (e.keyCode == '40') || (e.keyCode == '37') || (e.keyCode == '39') ) {
        fetch(document.location.origin+'/control?var=car&val=3');
		keyIsPressed = false;
    }
  
}

