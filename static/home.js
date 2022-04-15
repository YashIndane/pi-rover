//Calls API to run command
function run_command(){
	var command = document.getElementById("cli").value;
	var xhr = new XMLHttpRequest();
	var queryString = "http://<IP>:5500/command?cmd=" + command;

	//Go to API
	xhr.open("GET", queryString, true);
	xhr.send();
	xhr.onload = function(){
		//Get the response from API
		var output = xhr.responseText;
		//Writing the output on webpage
		document.getElementById("out").innerHTML = output;
	}
}


//Calls API to snap photo
function snap(){
	var xhr = new XMLHttpRequest();
	var queryString = "http://<IP>:5500/snap";

	//Go to API
	xhr.open("GET", queryString, true);
	xhr.send();
}
