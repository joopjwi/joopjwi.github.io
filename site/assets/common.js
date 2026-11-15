/* 줍쥐 공통: 분석 이벤트, 공유, 토스트 */
(function(){
  var cfg = window.JOOPJWI_CONFIG || {};
  // GA4: config.js에 측정 ID를 넣으면 켜짐
  if (cfg.ga4) {
    var s = document.createElement("script");
    s.async = true; s.src = "https://www.googletagmanager.com/gtag/js?id=" + cfg.ga4;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function(){ dataLayer.push(arguments); };
    gtag("js", new Date()); gtag("config", cfg.ga4);
  }
  window.track = function(name, params){
    try { if (window.gtag) gtag("event", name, params || {}); } catch(e) {}
  };

  window.toast = function(msg){
    var t = document.getElementById("toast");
    if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; document.body.appendChild(t); }
    t.textContent = msg; t.style.display = "block";
    clearTimeout(t._h); t._h = setTimeout(function(){ t.style.display = "none"; }, 1800);
  };

  window.shareItem = function(url, title){
    var text = "이게 만원도 안 한다고? 🐭 줍쥐에서 발견한 가성비템!";
    track("share", { item_url: url });
    if (navigator.share) {
      navigator.share({ title: title || "줍쥐", text: text, url: url }).catch(function(){});
      return;
    }
    var full = text + "\n" + url;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(full).then(function(){ toast("링크를 복사했어요"); }, function(){ prompt("아래 링크를 복사하세요", url); });
    } else { prompt("아래 링크를 복사하세요", url); }
  };

  // 쿠팡 이동 클릭 추적 (data-go 속성이 있는 링크)
  document.addEventListener("click", function(e){
    var a = e.target.closest && e.target.closest("[data-go]");
    if (a) track("click_coupang", { item_id: a.getAttribute("data-go"), placement: a.getAttribute("data-place") || "" });
    var m = e.target.closest && e.target.closest("[data-menu]");
    if (m) { document.getElementById("sheet").classList.add("open"); }
    var c = e.target.closest && e.target.closest("[data-close]");
    if (c || (e.target.id === "sheet")) { document.getElementById("sheet").classList.remove("open"); }
  });
})();
