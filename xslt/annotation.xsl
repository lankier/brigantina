<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xlink="http://www.w3.org/1999/xlink"
                xmlns:fb="http://www.gribuser.ru/xml/fictionbook/2.0"
                exclude-result-prefixes="xlink fb">
<xsl:output method="html" omit-xml-declaration="yes" encoding="UTF-8"/>
<xsl:key name="note-link" match="fb:section" use="@id"/>
<xsl:template match="/">
<div class="annotation">
  <xsl:for-each select="fb:annotation">
    <xsl:call-template name="annotation"/>
  </xsl:for-each>
</div>
</xsl:template>

<!-- author template -->
<xsl:template name="author">
  <xsl:value-of select="fb:first-name"/>
  <xsl:text disable-output-escaping="no">&#032;</xsl:text>
  <xsl:value-of select="fb:middle-name"/>&#032;
  <xsl:text disable-output-escaping="no">&#032;</xsl:text>
  <xsl:value-of select="fb:last-name"/>
  <br/>
</xsl:template>
<!-- secuence template -->
<xsl:template name="sequence">
  <LI/>
  <xsl:value-of select="@name"/>
  <xsl:if test="@number">
    <xsl:text disable-output-escaping="no">,&#032;#</xsl:text>
    <xsl:value-of select="@number"/>
  </xsl:if>
  <xsl:if test="fb:sequence">
    <UL>
      <xsl:for-each select="fb:sequence">
        <xsl:call-template name="sequence"/>
      </xsl:for-each>
    </UL>
  </xsl:if>
  <!--      <br/> -->
</xsl:template>
<!-- toc template -->
<xsl:template match="fb:section|fb:body" mode="toc">
  <xsl:choose>
    <xsl:when test="name()='body' and position()=1 and not(fb:title)">
      <xsl:apply-templates select="fb:section" mode="toc"/>
    </xsl:when>
    <xsl:otherwise>
      <li>
        <a href="#TOC_{generate-id()}"><xsl:value-of select="normalize-space(fb:title/fb:p[1] | @name)"/></a>
        <xsl:if test="fb:section">
          <UL><xsl:apply-templates select="fb:section" mode="toc"/></UL>
        </xsl:if>
      </li>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>
<!-- description -->
<xsl:template match="fb:description">
  <xsl:apply-templates/>
</xsl:template>
<!-- body -->
<xsl:template match="fb:body">
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="fb:section">
  <a name="TOC_{generate-id()}"></a>
  <xsl:if test="@id">
    <xsl:element name="a">
      <xsl:attribute name="name"><xsl:value-of select="@id"/></xsl:attribute>
    </xsl:element>
  </xsl:if>
  <xsl:apply-templates/>
</xsl:template>


<!-- section/title -->
<xsl:template match="fb:section/fb:title|fb:poem/fb:title">
  <xsl:choose>
    <xsl:when test="count(ancestor::node()) &lt; 9">
      <xsl:element name="{concat('h',count(ancestor::node())-3)}">
        <a name="TOC_{generate-id()}"></a>
        <xsl:if test="@id">
          <xsl:element name="a">
            <xsl:attribute name="name"><xsl:value-of select="@id"/></xsl:attribute>
          </xsl:element>
        </xsl:if>
        <xsl:apply-templates/>
      </xsl:element>
    </xsl:when>
    <xsl:otherwise>
      <xsl:element name="h6">
        <xsl:if test="@id">
          <xsl:element name="a">
            <xsl:attribute name="name"><xsl:value-of select="@id"/></xsl:attribute>
          </xsl:element>
        </xsl:if>
        <xsl:apply-templates/>
      </xsl:element>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>
<!-- section/title -->
<xsl:template match="fb:body/fb:title">
  <h1><xsl:apply-templates/></h1>
</xsl:template>

<xsl:template match="fb:title/fb:p|fb:title-info/fb:book-title">
  <xsl:apply-templates/><br/>
</xsl:template>
<!-- subtitle -->
<xsl:template match="fb:subtitle">
  <xsl:if test="@id">
    <xsl:element name="a">
      <xsl:attribute name="name"><xsl:value-of select="@id"/></xsl:attribute>
    </xsl:element>
  </xsl:if>
  <h5>
    <xsl:apply-templates/>
  </h5>
</xsl:template>
<!-- p -->
<xsl:template match="fb:p">
  <p class="paragraph"><xsl:if test="@id">
    <xsl:element name="a">
      <xsl:attribute name="name"><xsl:value-of select="@id"/></xsl:attribute>
    </xsl:element>
  </xsl:if><xsl:apply-templates/></p>
</xsl:template>

<!-- sub -->
<xsl:template match="fb:sub">
  <sub><xsl:apply-templates/></sub>
</xsl:template>
<!-- sup -->
<xsl:template match="fb:sup">
  <sup><xsl:apply-templates/></sup>
</xsl:template>
<!-- strong -->
<xsl:template match="fb:strong">
  <b><xsl:apply-templates/></b>
</xsl:template>
<!-- emphasis -->
<xsl:template match="fb:emphasis">
  <i><xsl:apply-templates/></i>
</xsl:template>
<!-- style -->
<xsl:template match="fb:style">
  <span class="{@name}"><xsl:apply-templates/></span>
</xsl:template>
<!-- code -->
<xsl:template match="fb:code">
  <tt><xsl:apply-templates/></tt>
</xsl:template>
<!-- strikethrough -->
<xsl:template match="fb:strikethrough">
  <s><xsl:apply-templates/></s>
</xsl:template>
<!-- empty-line -->
<xsl:template match="fb:empty-line">
  <br/>
</xsl:template>
<!-- link -->
<xsl:template match="fb:a">
  <xsl:element name="a">
    <xsl:attribute name="href"><xsl:value-of select="@xlink:href"/></xsl:attribute>
    <xsl:attribute name="title">
      <xsl:choose>
        <xsl:when test="starts-with(@xlink:href,'#')"><xsl:value-of select="key('note-link',substring-after(@xlink:href,'#'))/fb:p"/></xsl:when>
        <xsl:otherwise><xsl:value-of select="key('note-link',@xlink:href)/fb:p"/></xsl:otherwise>
      </xsl:choose>
    </xsl:attribute>
    <xsl:choose>
      <xsl:when test="(@type) = 'note'">
        <sup>
          <xsl:apply-templates/>
        </sup>
      </xsl:when>
      <xsl:otherwise>
        <xsl:apply-templates/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:element>
</xsl:template>
<!-- annotation -->
<xsl:template name="annotation">
  <xsl:if test="@id">
    <xsl:element name="a">
      <xsl:attribute name="name"><xsl:value-of select="@id"/></xsl:attribute>
    </xsl:element>
  </xsl:if>
  <xsl:apply-templates/>
</xsl:template>
<!-- epigraph -->
<xsl:template match="fb:epigraph">
  <blockquote class="epigraph">
    <xsl:if test="@id">
      <xsl:element name="a">
        <xsl:attribute name="name"><xsl:value-of select="@id"/></xsl:attribute>
      </xsl:element>
    </xsl:if>
    <xsl:apply-templates/>
  </blockquote>
</xsl:template>
<!-- epigraph/text-author -->
<xsl:template match="fb:epigraph/fb:text-author">
  <blockquote class="epigraph">
    <i><xsl:apply-templates/></i>
  </blockquote>
</xsl:template>
<!-- cite -->
<xsl:template match="fb:cite">
  ...<blockquote class="cite"><i>
  <xsl:if test="@id">
    <xsl:element name="a">
      <xsl:attribute name="name"><xsl:value-of select="@id"/></xsl:attribute>
    </xsl:element>
  </xsl:if>
  <xsl:apply-templates/>
</i></blockquote>
</xsl:template>
<!-- cite/text-author -->
<xsl:template name="text-author">
  <br/>
  <i>	<xsl:apply-templates/></i>
</xsl:template>
<!-- date -->
<xsl:template match="fb:date">
  <xsl:choose>
    <xsl:when test="not(@value)">
      &#160;&#160;&#160;<xsl:apply-templates/>
      <br/>
    </xsl:when>
    <xsl:otherwise>
      &#160;&#160;&#160;<xsl:value-of select="@value"/>
      <br/>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>
<!-- poem -->
<xsl:template match="fb:poem">
  <blockquote class="poem">
    <xsl:if test="@id">
      <xsl:element name="a">
        <xsl:attribute name="name"><xsl:value-of select="@id"/></xsl:attribute>
      </xsl:element>
    </xsl:if>
    <xsl:apply-templates/>
  </blockquote>
</xsl:template>
<!-- poem/title -->
<!--	<xsl:template match="fb:poem/fb:title">
    <h6><xsl:apply-templates/></h6>
    </blockquote>
    </xsl:template> -->
<!-- stanza -->
<xsl:template match="fb:stanza">
  <br/>
  <xsl:apply-templates/>
  <br/>
</xsl:template>
<!-- v -->
<xsl:template match="fb:v">
  <xsl:if test="@id">
    <xsl:element name="a">
      <xsl:attribute name="name"><xsl:value-of select="@id"/></xsl:attribute>
    </xsl:element>
  </xsl:if>
  <xsl:apply-templates/><br/>
</xsl:template>
<!-- image -->
<xsl:template match="fb:image">
  <div align="center">
    <img border="1">
      <xsl:choose>
        <xsl:when test="starts-with(@xlink:href,'#')">
          <xsl:attribute name="src"><xsl:value-of select="substring-after(@xlink:href,'#')"/></xsl:attribute>
        </xsl:when>
        <xsl:otherwise>
          <xsl:attribute name="src"><xsl:value-of select="@xlink:href"/></xsl:attribute>
        </xsl:otherwise>
      </xsl:choose>
    </img>
  </div>
</xsl:template>
</xsl:stylesheet>
