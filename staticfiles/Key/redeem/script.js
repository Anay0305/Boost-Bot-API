async function Redeemclick() {
    var redeemCode = document.getElementById("redeemCode")
    var redeemKey = redeemCode.value;
    var redeemMessage = document.getElementById("redeemMessage");
    var redeemButton = document.getElementById("redeemButton");
    var serverInvite = document.getElementById("serverInvite");

    if (redeemKey === "") {
        redeemMessage.innerHTML = "Please enter a code.";
        redeemMessage.style.color = "red";
        redeemMessage.classList.remove("hide");
        return;
    }
    else if (serverInvite.value === "") {
        redeemMessage.innerHTML = "Please enter a server invite.";
        redeemMessage.style.color = "red";
        redeemMessage.classList.remove("hide");
        return;
    }
    const payload = { 'key': redeemKey };
    const response = await fetch(`${window.location.origin}/api/key/get_info`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });
    
    if (response.status === 500) {
        redeemMessage.innerHTML = "Server error. Please try again later.";
        redeemMessage.style.color = "red";
        redeemMessage.classList.remove("hide");
        return;
    } else if (response.status === 200) {
        const data = await response.json();
        if ("error" in data) {
            redeemMessage.innerHTML = "Invalid code. Please check and try again.";
            redeemMessage.style.color = "red";
            redeemMessage.classList.remove("hide");
            return;
        }
        else {
            if (data["status"] === "Redeemed") {
                redeemMessage.innerHTML = "This code has already been Redeemed.";
                redeemMessage.style.color = "red";
                redeemMessage.classList.remove("hide");
                return;
            }
            redeemButton.innerHTML = 'Redeeming <span class="spinner"></span>';
            redeemCode.disabled = true;
            serverInvite.disabled = true;
            redeemButton.disabled = true;
            const payload = { 'key': redeemKey, 'invite': serverInvite.value };
            const response = await fetch(`${window.location.origin}/api/key/redeem_key`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });
            const data1 = await response.json();
            if (data1['status'] === false) {
                redeemMessage.innerHTML = data1['message'];
                redeemMessage.style.color = "red";
                redeemMessage.classList.remove("hide");
                redeemButton.innerHTML = "Redeem";
                redeemCode.disabled = false;
                serverInvite.disabled = false;
                redeemButton.disabled = false;
                return;
            } else if (data1['status'] === true) {
                window.location.href = `/key/info/?key=${redeemKey}`;
        }}
    } else {
        redeemMessage.innerHTML = "Unknown error. Please try again later.";
        redeemMessage.style.color = "red";
        redeemMessage.classList.remove("hide");
        return;
    }
}