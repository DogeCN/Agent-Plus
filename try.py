from parts.parser import Parser

data = r"""<shell timeout=10>
$desktop = "C:\Users\Doge\Desktop"
$filePath = Join-Path $desktop "东莞天气周报.html"
if (Test-Path $filePath) {
    Write-Host "文件已存在，路径: $filePath"
    # 尝试在默认浏览器中打开
    Start-Process $filePath
    Write-Host "已在浏览器中打开"
} else {
    Write-Host "文件不存在，正在重新创建..."
    $htmlContent = @'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>东莞天气周报 | 2026年4月26日 — 5月2日</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #e8f0ff 0%, #f0f4fa 100%);
            min-height: 100vh;
            padding: 24px 20px 48px;
            color: #1e293b;
        }

        .container {
            max-width: 1300px;
            margin: 0 auto;
        }

        /* 头部卡片 */
        .header-card {
            background: white;
            border-radius: 32px;
            padding: 28px 32px;
            margin-bottom: 28px;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.05);
        }

        h1 {
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        h1 span {
            background: #f59e0b;
            color: white;
            font-size: 0.9rem;
            font-weight: 500;
            padding: 4px 12px;
            border-radius: 40px;
        }

        .date-range {
            color: #5b6e8c;
            margin-bottom: 24px;
            font-size: 0.95rem;
            border-left: 3px solid #3b82f6;
            padding-left: 12px;
        }

        .stats-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            margin-top: 16px;
        }

        .stat-item {
            flex: 1;
            min-width: 140px;
            background: #f8fafc;
            border-radius: 20px;
            padding: 16px 20px;
            text-align: center;
        }

        .stat-label {
            font-size: 0.85rem;
            color: #5b6e8c;
            margin-bottom: 6px;
        }

        .stat-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #0f172a;
        }

        .stat-unit {
            font-size: 0.9rem;
            font-weight: 400;
            color: #5b6e8c;
        }

        /* 7天预报表格 */
        .forecast-section {
            background: white;
            border-radius: 32px;
            padding: 24px 24px 32px;
            margin-bottom: 28px;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.05);
        }

        .section-title {
            font-size: 1.4rem;
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .section-title .icon {
            font-size: 1.5rem;
        }

        .weather-table-wrapper {
            overflow-x: auto;
            border-radius: 20px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 680px;
        }

        th {
            background: #f1f5f9;
            padding: 14px 12px;
            font-weight: 600;
            color: #334155;
            text-align: center;
            font-size: 0.9rem;
        }

        td {
            padding: 14px 12px;
            text-align: center;
            border-bottom: 1px solid #e6edf4;
            vertical-align: middle;
        }

        .weather-icon {
            font-size: 1.6rem;
        }

        .temp-high {
            font-weight: 700;
            color: #dc2626;
        }

        .temp-low {
            font-weight: 500;
            color: #3b82f6;
        }

        .rain-badge {
            background: #dbeafe;
            color: #1d4ed8;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 500;
            display: inline-block;
        }

        .warning-tag {
            background: #fee2e2;
            color: #b91c1c;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 500;
            display: inline-block;
        }

        /* 提醒卡片 */
        .tips-wrapper {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 28px;
        }

        .tip-card {
            background: white;
            border-radius: 24px;
            padding: 20px 24px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
            transition: transform 0.2s;
        }

        .tip-card:hover {
            transform: translateY(-2px);
        }

        .tip-card h3 {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .tip-card p {
            color: #475569;
            line-height: 1.5;
            font-size: 0.9rem;
        }

        .footer-note {
            text-align: center;
            color: #6c7a91;
            font-size: 0.75rem;
            margin-top: 28px;
            padding-top: 16px;
            border-top: 1px solid #e2e8f0;
        }

        @media (max-width: 640px) {
            body { padding: 16px; }
            .header-card { padding: 20px; }
            h1 { font-size: 1.4rem; }
            .stat-value { font-size: 1.4rem; }
        }
    </style>
</head>
<body>
<div class="container">
    <!-- 头部卡片 -->
    <div class="header-card">
        <h1>
            🌤️ 东莞天气周报
            <span>2026年第17周</span>
        </h1>
        <div class="date-range">📅 2026年4月26日 (周日) — 2026年5月2日 (周六)</div>
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-label">🗓️ 本周最高温</div>
                <div class="stat-value">30<span class="stat-unit">℃</span></div>
            </div>
            <div class="stat-item">
                <div class="stat-label">❄️ 本周最低温</div>
                <div class="stat-value">19<span class="stat-unit">℃</span></div>
            </div>
            <div class="stat-item">
                <div class="stat-label">🌧️ 降水天数</div>
                <div class="stat-value">5<span class="stat-unit">天</span></div>
            </div>
            <div class="stat-item">
                <div class="stat-label">🌬️ 主导风向</div>
                <div class="stat-value">东南<span class="stat-unit"></span></div>
            </div>
        </div>
    </div>

    <!-- 7天预报表格 -->
    <div class="forecast-section">
        <div class="section-title">
            <span class="icon">📋</span> 未来七天逐日预报
        </div>
        <div class="weather-table-wrapper">
            <table>
                <thead>
                <tr>
                    <th>日期</th>
                    <th>星期</th>
                    <th>天气</th>
                    <th>高温 / 低温</th>
                    <th>风力风向</th>
                    <th>日出 / 日落</th>
                    <th>提醒</th>
                </tr>
                </thead>
                <tbody>
                <!-- 数据基于 NMC.cn / yzqxj.com / ip.cn 等多方来源综合 -->
                <tr>
                    <td><strong>4月26日</strong></td>
                    <td>周日</div>多云转阴</div>
                    <td><span class="temp-high">29°C</span> / <span class="temp-low">20°C</span></div>
                    <td>东南风 2级</div>
                    <td>05:56 / 18:49</div>
                    <td><span class="rain-badge">🌿 适宜户外</span></div>
                </tr>
                <tr>
                    <td><strong>4月27日</strong></div>
                    <td>周一</div>
                    <td><div class="weather-icon">⛈️</div>雷阵雨</div>
                    <td><span class="temp-high">30°C</span> / <span class="temp-low">22°C</span></div>
                    <td>南风转北风 &lt;3级</div>
                    <td>05:57 / 18:51</div>
                    <td><span class="warning-tag">⚠️ 带雨具·防雷暴</span></div>
                </tr>
                <tr>
                    <td><strong>4月28日</strong></div>
                    <td>周二</div>
                    <td><div class="weather-icon">🌧️</div>中雨转大雨</div>
                    <td><span class="temp-high">27°C</span> / <span class="temp-low">21°C</span></div>
                    <td>北风转东风 &lt;3级</div>
                    <td>05:56 / 18:51</div>
                    <td><span class="warning-tag">⛈️ 暴雨黄色预警风险</span></div>
                </tr>
                <tr>
                    <td><strong>4月29日</strong></div>
                    <td>周三</div>
                    <td><div class="weather-icon">⛈️</div>雷阵雨转大雨</div>
                    <td><span class="temp-high">26°C</span> / <span class="temp-low">18°C</span></div>
                    <td>东南风 &lt;3级</div>
                    <td>05:55 / 18:51</div>
                    <td><span class="warning-tag">🌊 短时强降水警惕</span></div>
                </tr>
                <tr>
                    <td><strong>4月30日</strong></div>
                    <td>周四</div>
                    <td><div class="weather-icon">🌦️</div>雷阵雨转多云</div>
                    <td><span class="temp-high">26°C</span> / <span class="temp-low">19°C</span></div>
                    <td>南风 &lt;3级</div>
                    <td>05:55 / 18:52</div>
                    <td><span class="rain-badge">🌂 仍有阵雨</span></div>
                </tr>
                <tr>
                    <td><strong>5月1日</strong></div>
                    <td>周五</div>
                    <td><div class="weather-icon">☁️</div>多云转阴</div>
                    <td><span class="temp-high">27°C</span> / <span class="temp-low">21°C</span></div>
                    <td>东南风 &lt;3级</div>
                    <td>05:54 / 18:52</div>
                    <td><span class="rain-badge">🚗 劳动节出行注意</span></div>
                </tr>
                <tr>
                    <td><strong>5月2日</strong></div>
                    <td>周六</div>
                    <td><div class="weather-icon">🌧️</div>小雨</div>
                    <td><span class="temp-high">28°C</span> / <span class="temp-low">21°C</span></div>
                    <td>南风转东南风 &lt;3级</div>
                    <td>05:53 / 18:53</div>
                    <td><span class="warning-tag">💧 持续降水</span></div>
                </tr>
                </tbody>
            </table>
        </div>
        <p style="font-size: 0.75rem; color: #6c7a91; margin-top: 16px;">※ 
数据综合自中国天气网、东莞市气象台等权威发布，预报信息会实时更新，建议出行前再次确认。</p>
    </div>

    <!-- 本周重点提醒卡片 -->
    <div class="tips-wrapper">
        <div class="tip-card">
            <h3>⛈️ 强对流天气预警</h3>
            <p>据东莞市气象台预报，<strong>27—29日</strong>将有一次明显雷雨、大风天气过程，局地伴有8级短时大风。请妥善收起阳台花盆、加固临时搭建物；突遇雷
暴时迅速进入室内，不在大树、临时工棚附近逗留。</p>
        </div>
        <div class="tip-card">
            <h3>🧥 穿衣与体感建议</h3>
            <p>本周前期（26日）较为温暖舒适；27—29日降雨时段体感略凉，可备薄外套；后期25—27℃之间湿度偏高，建议穿着透气衣物，随身携带雨具。</p>
        </div>
        <div class="tip-card">
            <h3>🚗 城市内涝风险提醒</h3>
            <p>未来雷雨天气较频繁，短时强降水可能导致低洼路段积水，驾车出行请减速慢行，尽量避开涵洞、隧道等易积水区域。关注最新预警信息，提前规划路线。</p
>
        </div>
        <div class="tip-card">
            <h3>🌅 日出日落与紫外线</h3>
            <p>本周太阳高度渐升，日出时间约在05:53—05:57，日落约18:49—18:53。26日紫外线指数中等，户外活动建议涂抹防晒霜；降水时段紫外线弱，但仍需注意飘雨
时能见度。</p>
        </div>
    </div>

    <div class="footer-note">
        🌸 数据来源：中国天气网 (NMC.cn) 、东莞市气象台、yzqxj.com、ip.cn 等 📍 统计时间：2026年4月26日 · 东莞
    </div>
</div>
</body>
</html>
'@
    Set-Content -Path $filePath -Value $htmlContent -Encoding UTF8
    if (Test-Path $filePath) {
        Write-Host "文件创建成功: $filePath"
        Start-Process $filePath
        Write-Host "已在浏览器中打开"
    } else {
        Write-Host "文件创建失败，请检查权限"
    }
}
</shell>"""

parser = Parser()
for c in data:
    if parser.update(c):
        break

print(parser.get())  # None
