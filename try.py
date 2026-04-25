from parts.parser import Parser

data = r"""<shell timeout=30>
$city = "Dongguan"
$url = "https://wttr.in/$city?format=j1"
$response = Invoke-WebRequest -Uri $url -UseBasicParsing
$data = $response.Content | ConvertFrom-Json

$days = $data.weather[0..6]  # 今天 + 未来6天
$html = @"
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>东莞本周天气报表</title>
<style>
body { font-family: Arial; margin: 20px; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
th { background-color: #4CAF50; color: white; }
tr:nth-child(even) { background-color: #f2f2f2; }
</style>
</head>
<body>
<h2>东莞本周天气报表 ( $($days[0].date) 至 $($days[-1].date) )</h2>
<table>
<tr><th>日期</th><th>天气</th><th>最高温(°C)</th><th>最低温(°C)</th><th>降雨概率</th></tr>
"@

foreach ($day in $days) {
    $date = $day.date
    $desc = $day.hourly[0].weatherDesc[0].value
    $max = $day.maxtempC
    $min = $day.mintempC
    $pop = $day.hourly[0].chanceofrain
    $html += "<tr><td>$date</td><td>$desc</td><td>$max</td><td>$min</td><td>$pop%</td></tr>`n"
}

$html += "</table><p>数据来源: wttr.in</p></body></html>"

$outFile = "$env:TEMP\weather_report.html"
$html | Out-File -FilePath $outFile -Encoding UTF8
Start-Process $outFile
Write-Output "已生成天气报表并打开: $outFile"
</shell>"""

parser = Parser()
for c in data:
    if parser.update(c):
        break

print(parser.get())  # None
