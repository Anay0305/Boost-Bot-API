function copyToClipboard(text) {
    var textArea = document.createElement('textarea');
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    textArea.setSelectionRange(0, 99999);
    document.execCommand('copy');
    document.body.removeChild(textArea);            
    showCopyMessage('Copied to clipboard: ' + text);
}
function showCopyMessage(message) {
    var messageBox = document.createElement('div');
    messageBox.textContent = message;
    messageBox.style.position = 'fixed';
    messageBox.style.top = '10px';
    messageBox.style.left = '50%';
    messageBox.style.transform = 'translateX(-50%)';
    messageBox.style.backgroundColor = '#333';
    messageBox.style.color = '#fff';
    messageBox.style.padding = '10px 20px';
    messageBox.style.fontSize = '16px';
    messageBox.style.borderRadius = '5px';
    messageBox.style.boxShadow = '0 4px 10px rgba(0, 0, 0, 0.3)';
    messageBox.style.zIndex = '9999';
    messageBox.style.opacity = '1';
    messageBox.style.transition = 'opacity 1s ease-out';

    document.body.appendChild(messageBox);
    setTimeout(function() {
        messageBox.style.opacity = '0';
        setTimeout(function() {
            document.body.removeChild(messageBox);
        }, 1000);
    }, 3000);
}