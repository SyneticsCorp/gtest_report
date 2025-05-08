/**
 * @brief 상세 정보를 토글하는 함수
 * @param {string} divId 토글할 div의 id
 */
function ShowDiv(divId) {
    var x = document.getElementById(divId);
    if (x.style.display === "none" || x.style.display === "") {
        x.style.display = "block";
    } else {
        x.style.display = "none";
    }
}
