function toTitleCase(txt)
{
    return txt.charAt(0).toUpperCase() + txt.substr(1);
}

function getDisplayedName() {
	var firstName = document.getElementById('id_first_name').value;
	var lastName = document.getElementById('id_last_name').value;
	if (firstName != "" && lastName != "") {
		return toTitleCase(firstName) + " " + toTitleCase(lastName);
	} else if (lastName != "") {
		return toTitleCase(lastName);
	} else if (firstName != "") {
		return toTitleCase(firstName);		
	} else {
		return toTitleCase(document.getElementById('id_username').value);
	}
}

function refreshDisplayedName() {
	displayed_name = document.getElementById('displayed_name');
	if (displayed_name.innerText) {
		displayed_name.innerText = getDisplayedName();
	} else {
		displayed_name.textContent = getDisplayedName();
	} 
}

setInterval("refreshDisplayedName()", 500);
