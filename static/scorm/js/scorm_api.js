let API = null;

function findAPI() {
    if (API) return API;
    if (window.parent && window.parent.API) return window.parent.API;
    if (window.top && window.top.API) return window.top.API;
    return null;
}

function initializeSCORM() {
    API = findAPI();
    if (API) {
        API.LMSInitialize("");
        API.LMSSetValue("cmi.core.lesson_status", "completed");
    }
}

function sendScore() {
    if (!API) initializeSCORM();

    try {
        API.LMSSetValue("cmi.core.score.raw", "100");
        API.LMSSetValue("cmi.core.score.max", "100");
        API.LMSSetValue("cmi.core.score.min", "0");
        API.LMSCommit("");
        API.LMSFinish("");
        window.top.location.href = "https://sc-learn.ru/mod/page/view.php?id=349";
    } catch (e) {
        alert("Ошибка: " + e);
    }
}

window.onload = initializeSCORM;
window.onunload = function() {
    if (API) API.LMSFinish("");
};
