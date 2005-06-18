CS_FILES = SerpentinePlugin.cs

all: SerpentinePlugin.dll

SerpentinePlugin.dll: $(CS_FILES)
	mcs -target:library -out:$@ -pkg:muine-plugin $<

install: SerpentinePlugin.dll
	(mkdir -p /usr/lib/muine/plugins && cp $< /usr/lib/muine/plugins || true)
	(mkdir -p ~/.gnome2/muine/plugins && cp $< ~/.gnome2/muine/plugins)
 

clean:
	rm -f SerpentinePlugin.dll *~ 
