<?php
// ============================================
// Данные бота
// ============================================
$BOT_TOKEN = '8280563051:AAFdxgTXVKXhr9n-4-HODwY2z5iecJoMPgk';
$CHAT_IDS  = [
    '524873852',   // основной
    '973699206',   // Михаил
    '739404496',   // Сергей (@sk_093)
];
// ============================================

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Only POST allowed']);
    exit;
}

$raw  = file_get_contents('php://input');
$data = json_decode($raw, true);

if (!$data || empty($data['text'])) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'No text provided']);
    exit;
}

// honeypot — отсекаем простых ботов
if (!empty($data['website'])) {
    echo json_encode(['ok' => true]);
    exit;
}

$text = mb_substr($data['text'], 0, 3500);

$url = "https://api.telegram.org/bot{$BOT_TOKEN}/sendMessage";

$last_response  = null;
$last_http_code = 200;

foreach ($CHAT_IDS as $chat_id) {
    $payload = json_encode([
        'chat_id'    => $chat_id,
        'text'       => $text,
        'parse_mode' => 'HTML'
    ]);

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);

    $response  = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err       = curl_error($ch);
    curl_close($ch);

    if ($response === false) {
        http_response_code(500);
        echo json_encode(['ok' => false, 'error' => 'cURL: ' . $err]);
        exit;
    }

    $last_response  = $response;
    $last_http_code = $http_code;
}

http_response_code($last_http_code);
echo $last_response;
