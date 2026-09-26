/* A "copy" button on every code block.

   Progressive enhancement: without this file the code is still there to be
   selected by hand, and no dead button is shown - the buttons are created
   here. Loaded only on pages that contain a code block.

   ES5, no dependency, no network, no storage, and no text of its own: the
   button's wording comes from content/site.toml ([labels] copy, copied),
   written by the build on this script's tag as data-copy and data-copied.
   It copies the code as text, without the highlighting. */

(function () {
	"use strict";

	var me = document.currentScript;
	var copy = (me && me.getAttribute("data-copy")) || "copy";
	var copied = (me && me.getAttribute("data-copied")) || "ok";

	function fallback(text) {
		// Older browsers, or a page not served over HTTPS.
		var area = document.createElement("textarea");
		area.value = text;
		area.setAttribute("readonly", "");
		area.style.position = "absolute";
		area.style.left = "-9999px";
		document.body.appendChild(area);
		area.select();
		var ok = false;
		try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
		document.body.removeChild(area);
		return ok;
	}

	function done(button) {
		button.textContent = copied;
		button.setAttribute("data-state", "done");
		live.textContent = copied;
		setTimeout(function () {
			button.textContent = copy;
			button.removeAttribute("data-state");
			live.textContent = "";
		}, 2000);
	}

	// Announces "copied" to screen readers; the button's text change alone
	// is not reliably read.
	var live = document.createElement("p");
	live.className = "sr-only";
	live.setAttribute("aria-live", "polite");
	document.body.appendChild(live);

	var blocks = document.querySelectorAll("pre.code");
	for (var i = 0; i < blocks.length; i++) {
		(function (pre) {
			var code = pre.querySelector("code") || pre;
			var button = document.createElement("button");
			button.type = "button";
			button.className = "copy";
			button.textContent = copy;
			button.onclick = function () {
				var text = code.textContent;
				if (navigator.clipboard && window.isSecureContext) {
					navigator.clipboard.writeText(text).then(function () {
						done(button);
					}, function () {
						if (fallback(text)) done(button);
					});
				} else if (fallback(text)) {
					done(button);
				}
			};
			// Outside the <pre>, which scrolls sideways: the button stays put.
			var wrap = document.createElement("div");
			wrap.className = "code-wrap";
			pre.parentNode.insertBefore(wrap, pre);
			wrap.appendChild(pre);
			wrap.appendChild(button);
		}(blocks[i]));
	}
}());
