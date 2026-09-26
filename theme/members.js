/* Search and category filter for /members - the site's only script.

   Progressive enhancement: the full list is in the HTML and readable
   without this file. The controls are created here, so a visitor without
   JavaScript never sees a search box that does nothing.

   ES5, no dependency, no network, no storage, and no text of its own: the
   wording comes from content/site.toml ([members]), which the build writes
   on the grid as data-search_label, data-search_placeholder, data-all, data-one,
   data-many and data-none. Each card carries its own data:
     data-search    first, last and display name, ASCII-folded, lowercase
     data-category  admin, mentor, membre, ...
   The CSP allows the site's own script files only (Caddyfile, AGENTS.md §4.4). */

(function () {
	"use strict";

	var grid = document.querySelector(".b.members");
	if (!grid) return;
	var cards = grid.querySelectorAll(".entry[data-search]");
	if (!cards.length) return;

	function text(name) { return grid.getAttribute("data-" + name) || ""; }

	// Same folding as the build: accents off, lowercase.
	function fold(s) {
		s = String(s).toLowerCase();
		if (s.normalize) s = s.normalize("NFD").replace(/[̀-ͯ]/g, "");
		return s.replace(/\s+/g, " ").replace(/^ | $/g, "");
	}

	// Categories in the order the build sorted the cards.
	var categories = [];
	for (var i = 0; i < cards.length; i++) {
		var c = cards[i].getAttribute("data-category");
		if (categories.indexOf(c) < 0) categories.push(c);
	}

	var box = document.createElement("div");
	box.className = "filter";
	box.setAttribute("role", "search");

	var label = document.createElement("label");
	label.setAttribute("for", "filter-q");
	label.textContent = text("search_label");
	var input = document.createElement("input");
	input.type = "search";
	input.id = "filter-q";
	input.placeholder = text("search_placeholder");
	input.setAttribute("autocomplete", "off");
	input.setAttribute("spellcheck", "false");

	var buttons = document.createElement("div");
	buttons.className = "filter-cats";
	buttons.setAttribute("role", "group");
	buttons.setAttribute("aria-label", text("search_label"));

	var status = document.createElement("p");
	status.className = "filter-status";
	status.setAttribute("aria-live", "polite");

	var current = "";

	function button(value, text) {
		var b = document.createElement("button");
		b.type = "button";
		b.textContent = text;
		b.setAttribute("aria-pressed", value === current ? "true" : "false");
		b.onclick = function () {
			current = value;
			var all = buttons.querySelectorAll("button");
			for (var j = 0; j < all.length; j++) all[j].setAttribute("aria-pressed", "false");
			b.setAttribute("aria-pressed", "true");
			apply();
		};
		buttons.appendChild(b);
	}

	button("", text("all"));
	for (var k = 0; k < categories.length; k++) button(categories[k], categories[k]);

	function apply() {
		var words = fold(input.value).split(" ");
		var shown = 0;
		for (var n = 0; n < cards.length; n++) {
			var card = cards[n];
			var hay = card.getAttribute("data-search");
			var ok = !current || card.getAttribute("data-category") === current;
			for (var w = 0; ok && w < words.length; w++) {
				if (words[w] && hay.indexOf(words[w]) < 0) ok = false;
			}
			card.hidden = !ok;
			if (ok) shown++;
		}
		status.textContent = shown === 0 ? text("none")
			: shown + " " + text(shown > 1 ? "many" : "one");
	}

	input.oninput = apply;

	box.appendChild(label);
	box.appendChild(input);
	box.appendChild(buttons);
	box.appendChild(status);
	// Inside the grid, spanning every column (see .filter in style.css).
	grid.insertBefore(box, grid.firstChild);
	apply();
}());
