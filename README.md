sync-rhythmbox-scratchlive
--------------------------

sync-rhythmbox-scratchlive minimally syncs a scratchlivedb file with a
rhythmbox DB. Here's how I use it in my music org process:

- Download a bunch of music on my linux machine
- Organize it, put it into ~/Music, which is shared with my windows box
- Run rhythmbox, it picks up the new files, use rhythmbox to tweak some tags
- Mount my windows _Serato_ folder at /mnt/laptop/serato
- ./sync-rhythmbox-scratchlive --in-place /mnt/laptop/serato/database\ V2 /path/to/rhythmdb.xml
- A backup library copy is stored in /mnt/laptop/serato if something went wrong
- Run 'rescan tags' in Scratch Live to pick up all the tag values

Yeah, convoluted, but for whatever reason Scratch Live likes to forget the
timestamps randomly when I sync manually on the windows machine, so everything
appears like it was added recently, which messes up how I access music.
