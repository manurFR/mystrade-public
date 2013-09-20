function setUpVisibility(callBackWhenChange) {
    var hidden = "hidden", visible = "visible";

    // Standards:
    if (hidden in document)
        document.addEventListener("visibilitychange", onchangevisibility);
    else if ((hidden = "mozHidden") in document)
        document.addEventListener("mozvisibilitychange", onchangevisibility);
    else if ((hidden = "webkitHidden") in document)
        document.addEventListener("webkitvisibilitychange", onchangevisibility);
    else if ((hidden = "msHidden") in document)
        document.addEventListener("msvisibilitychange", onchangevisibility);
    // IE 9 and lower:
    else if ('onfocusin' in document)
        document.onfocusin = document.onfocusout = onchangevisibility;
    // All others:
    else
        window.onpageshow = window.onpagehide = window.onfocus = window.onblur = onchangevisibility;

    function onchangevisibility (evt) {
        var v = 'visible', h = 'hidden',
            evtMap = {
                focus:v, focusin:v, pageshow:v, blur:h, focusout:h, pagehide:h
            };

        evt = evt || window.event;
        if (evt.type in evtMap)
            $("body").attr("visibilityState", evtMap[evt.type]);
        else
            $("body").attr("visibilityState", this[hidden] ? "hidden" : "visible");

        if (callBackWhenChange) {
            callBackWhenChange();
        }
    }

    $("body").attr("visibilityState", visible);
}