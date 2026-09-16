/* Mesure d'audience GoatCounter : événements sans cookie ni donnée personnelle.
 * Ne fait rien si GoatCounter n'est pas chargé (code absent, bloqueur de publicité, hors ligne). */
(function (root) {
  "use strict";

  class Analytics {
    constructor({ minIntervalMs = 2000 } = {}) {
      this.minIntervalMs = minIntervalMs;
      this.lastSent = new Map();
    }

    /** Vrai si le script GoatCounter est chargé et prêt. */
    get ready() {
      const gc = root.goatcounter;
      return Boolean(gc && typeof gc.count === "function");
    }

    /** Envoie un événement nommé ; au plus un envoi par nom toutes les minIntervalMs. */
    track(eventName) {
      try {
        if (!this.ready || !eventName) return false;
        const now = Date.now();
        const last = this.lastSent.get(eventName) || 0;
        if (now - last < this.minIntervalMs) return false;
        this.lastSent.set(eventName, now);
        root.goatcounter.count({ path: eventName, event: true });
        return true;
      } catch (e) {
        return false; // jamais bloquant
      }
    }
  }

  root.Analytics = Analytics;
  if (typeof module === "object" && module.exports) module.exports = { Analytics };
})(typeof globalThis !== "undefined" ? globalThis : this);
