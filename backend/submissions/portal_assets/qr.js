/* Sporting Pearls — qr.js (Phase 7)
   Binds the Print button on the QR card pages (staff bulk, staff
   single, guardian single). External file — the portal CSP does not
   allow inline event handlers. Access: any signed-in user. */
(function () {
  "use strict";
  var b = document.getElementById("btn-print");
  if (b) b.addEventListener("click", function () { window.print(); });
})();
