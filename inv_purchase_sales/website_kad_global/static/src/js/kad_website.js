/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

function getScrollRoot() {
    return document.getElementById("wrapwrap") || document.scrollingElement || document.documentElement;
}

function scrollToTarget(target, headerOffset = 88) {
    const root = getScrollRoot();
    if (!target || !root) {
        return;
    }
    if (root === document.body || root === document.documentElement || root === document.scrollingElement) {
        const top = target.getBoundingClientRect().top + window.pageYOffset - headerOffset;
        window.scrollTo({ top, behavior: "smooth" });
        return;
    }
    const rootRect = root.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    const top = targetRect.top - rootRect.top + root.scrollTop - headerOffset;
    root.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
}

function animateCount(el, delay = 0) {
    const target = Number(el.dataset.kadCount || 0);
    const suffix = el.dataset.kadSuffix || "";
    const valueEl = el.querySelector(".kad-stat__value");
    if (!valueEl || Number.isNaN(target) || el.dataset.kadCounted === "1") {
        return;
    }
    el.dataset.kadCounted = "1";
    valueEl.textContent = `0${suffix}`;

    const finish = (value) => {
        valueEl.textContent = `${value}${suffix}`;
        el.classList.remove("is-counting");
        el.classList.add("is-counted");
    };

    const run = () => {
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            finish(target);
            return;
        }

        el.classList.add("is-counting");

        // Pace so each integer is readable: 1, 2, 3 … then settle on the total
        const msPerStep = target <= 40 ? 60 : target <= 150 ? 22 : 8;
        const duration = Math.min(3200, Math.max(1800, target * msPerStep));
        const start = performance.now();
        let lastShown = -1;

        const tick = (now) => {
            const progress = Math.min((now - start) / duration, 1);
            // Near-linear so early steps (1,2,3…) stay visible
            const eased = progress < 1 ? Math.pow(progress, 0.92) : 1;
            const current = Math.round(target * eased);
            if (current !== lastShown) {
                lastShown = current;
                valueEl.textContent = `${current}${suffix}`;
            }
            if (progress < 1) {
                requestAnimationFrame(tick);
            } else {
                finish(target);
            }
        };
        requestAnimationFrame(tick);
    };

    if (delay > 0) {
        window.setTimeout(run, delay);
    } else {
        run();
    }
}

function animateStatsIn(root) {
    const stats = root.classList.contains("kad-stat")
        ? [root]
        : [...root.querySelectorAll(".kad-stat[data-kad-count]")];
    stats.forEach((stat, index) => animateCount(stat, index * 160));
}

publicWidget.registry.KadWebsite = publicWidget.Widget.extend({
    selector: ".kad-site",
    events: {
        "click a[href^='#']": "_onAnchorClick",
    },

    start() {
        this.el.classList.add("kad-js-ready");
        this._setupReveals();
        this._bindGlobalAnchors();
        this._bindScrollChrome();
        this._bindParallax();
        return this._super(...arguments);
    },

    destroy() {
        if (this._globalClickHandler) {
            document.removeEventListener("click", this._globalClickHandler, true);
        }
        if (this._scrollHandler) {
            const root = getScrollRoot();
            root.removeEventListener("scroll", this._scrollHandler);
            window.removeEventListener("scroll", this._scrollHandler);
        }
        if (this._pointerHandler) {
            this.el.removeEventListener("pointermove", this._pointerHandler);
        }
        return this._super(...arguments);
    },

    _bindGlobalAnchors() {
        this._globalClickHandler = (event) => {
            const anchor = event.target.closest("a[href^='#']");
            if (!anchor || !document.querySelector(".kad-site")) {
                return;
            }
            this._scrollFromAnchor(event, anchor);
        };
        document.addEventListener("click", this._globalClickHandler, true);
    },

    _onAnchorClick(event) {
        this._scrollFromAnchor(event, event.currentTarget);
    },

    _scrollFromAnchor(event, anchor) {
        const id = anchor.getAttribute("href");
        if (!id || id === "#" || !id.startsWith("#")) {
            return;
        }
        const target = document.querySelector(id);
        if (!target) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        scrollToTarget(target);
        if (history.replaceState) {
            history.replaceState(null, "", id);
        }
    },

    _bindScrollChrome() {
        const root = getScrollRoot();
        const wrap = document.getElementById("wrapwrap");
        this._scrollHandler = () => {
            const y = root.scrollTop || window.pageYOffset || 0;
            if (wrap) {
                wrap.classList.toggle("kad-scrolled", y > 24);
            }
            document.body.classList.toggle("kad-scrolled", y > 24);
        };
        root.addEventListener("scroll", this._scrollHandler, { passive: true });
        window.addEventListener("scroll", this._scrollHandler, { passive: true });
        this._scrollHandler();
    },

    _bindParallax() {
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            return;
        }
        const orbs = this.el.querySelectorAll(".kad-orb");
        if (!orbs.length) {
            return;
        }
        this._pointerHandler = (event) => {
            const rect = this.el.getBoundingClientRect();
            const x = (event.clientX - rect.left) / rect.width - 0.5;
            const y = (event.clientY - rect.top) / rect.height - 0.5;
            orbs.forEach((orb, index) => {
                const strength = (index + 1) * 10;
                orb.style.setProperty("--mx", `${(x * strength).toFixed(1)}px`);
                orb.style.setProperty("--my", `${(y * strength).toFixed(1)}px`);
            });
        };
        this.el.addEventListener("pointermove", this._pointerHandler, { passive: true });
    },

    _setupReveals() {
        const nodes = this.el.querySelectorAll("[data-kad-anim]");
        nodes.forEach((node) => {
            const delay = Number(node.dataset.kadDelay || 0);
            if (delay) {
                node.style.setProperty("--kad-delay", `${delay}ms`);
            }
        });

        const revealNow = (node) => {
            if (node.classList.contains("is-visible") && node.dataset.kadRevealed === "1") {
                return;
            }
            node.dataset.kadRevealed = "1";
            node.classList.add("is-visible");
            if (node.classList.contains("kad-stats") || node.querySelector(".kad-stat[data-kad-count]")) {
                animateStatsIn(node);
            }

            // Unlock per-word hover after staggered entrance finishes
            const words = node.querySelectorAll(".kad-word, .kad-amp");
            if (words.length) {
                const maxDelay = 180 + (words.length - 1) * 120 + 800;
                window.setTimeout(() => {
                    words.forEach((word) => word.classList.add("is-live"));
                }, maxDelay);
            }
        };

        if (!("IntersectionObserver" in window)) {
            nodes.forEach(revealNow);
            return;
        }

        const scrollRoot = getScrollRoot();
        const observerRoot =
            scrollRoot && scrollRoot !== document.documentElement && scrollRoot !== document.body
                ? scrollRoot
                : null;

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (!entry.isIntersecting) {
                        return;
                    }
                    revealNow(entry.target);
                    observer.unobserve(entry.target);
                });
            },
            { root: observerRoot, threshold: 0.2, rootMargin: "0px 0px -10% 0px" }
        );

        nodes.forEach((node) => observer.observe(node));

        requestAnimationFrame(() => {
            const viewH = observerRoot ? observerRoot.clientHeight : window.innerHeight;
            nodes.forEach((node) => {
                const rect = node.getBoundingClientRect();
                if (rect.top < viewH * 0.88 && rect.bottom > 0) {
                    revealNow(node);
                    observer.unobserve(node);
                }
            });
        });
    },
});
