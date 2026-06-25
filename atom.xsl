<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:a="http://www.w3.org/2005/Atom">
  <xsl:output method="html" encoding="UTF-8" indent="yes"/>
  <xsl:template match="/">
    <html lang="zh-CN">
      <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title><xsl:value-of select="a:feed/a:title"/> · RSS 订阅源</title>
        <style>
          body{font-family:'Inter',system-ui,-apple-system,'PingFang SC',sans-serif;background:#FBF7EF;color:#2E2820;max-width:720px;margin:0 auto;padding:30px 20px;line-height:1.65}
          a{color:#B0801F;text-decoration:none}
          a:hover{text-decoration:underline}
          h1{font-size:23px;margin:0 0 4px;letter-spacing:-.01em}
          .sub{color:#6E6048;font-size:13px;margin-bottom:22px}
          .banner{background:#F2E9D6;border:1px solid rgba(150,110,40,.28);border-left:4px solid #B0801F;border-radius:12px;padding:16px 18px;margin-bottom:26px}
          .banner b{font-size:14px}
          .banner p{margin:7px 0 0;font-size:13px;color:#6E6048}
          code{background:#EBDDBE;padding:2px 8px;border-radius:5px;font-size:12px;word-break:break-all}
          .entry{border-top:1px solid rgba(150,110,40,.18);padding:16px 0}
          .entry .date{font-size:12px;color:#9C8B70;margin-bottom:5px;font-weight:600}
          .entry h2{font-size:16px;margin:0 0 6px;line-height:1.4}
          .entry .sum{font-size:13px;color:#6E6048}
          .foot{margin-top:26px;padding-top:16px;border-top:1px solid rgba(150,110,40,.18);font-size:12px;color:#9C8B70;text-align:center}
        </style>
      </head>
      <body>
        <h1>📡 <xsl:value-of select="a:feed/a:title"/></h1>
        <div class="sub"><xsl:value-of select="a:feed/a:subtitle"/></div>
        <div class="banner">
          <b>这是一个 RSS 订阅源（给阅读器用的，不是错误页）</b>
          <p>把本页地址 <code><xsl:value-of select="a:feed/a:link[@rel='self']/@href"/></code> 复制到任意 RSS 阅读器（Feedly / Inoreader / Reeder / Follow / NetNewsWire 等），每次发新日记都会自动推送给你——不用留邮箱，也不被算法过滤。</p>
          <p><a href="https://cynthia-git11.github.io/clawq-diary/">← 回到日记网站</a></p>
        </div>
        <xsl:for-each select="a:feed/a:entry">
          <div class="entry">
            <div class="date"><xsl:value-of select="substring(a:updated,1,10)"/></div>
            <h2><a href="{a:link/@href}"><xsl:value-of select="a:title"/></a></h2>
            <div class="sum"><xsl:value-of select="a:summary"/></div>
          </div>
        </xsl:for-each>
        <div class="foot">© 2026 天际资本 FutureX Capital · 张倩 Cynthia Zhang · 倩小虾日记</div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
