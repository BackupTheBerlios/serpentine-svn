
muineplugindir = $(libdir)/muine/plugins
muineplugin_DATA = SerpentinePlugin.dll
EXTRA_DIST = SerpentinePlugin.cs

SerpentinePlugin.dll: SerpentinePlugin.cs
	$(MCS) -target:library -out:$@ -pkg:muine-plugin $<

