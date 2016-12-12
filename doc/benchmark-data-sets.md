# Benchmark data sets

Data sets listed below:

* [15genome](benchmark-data-sets.md#15genome) - small & low memory, laptop-tractable.
* [mircea](benchmark-data-sets.md#mircea) - requires ~12 GB of RAM, ~90 seconds to load.
* [hu_catlas](benchmark-data-sets.md#hu_catlas) - cannot compute catlas for this one, even in 65 GB and 100 hours.

## 15genome

The `15genome` data set contains the first 15 genomes used to build
the mock community in the
[Shakya et al., 2014](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3665634/)
paper.  This is a labeled data set - the cDBG components corresponding to
each genome are labeled, and MinHash signatures are provided for use.

CTB TODO: provide full build instructions, including signature computation.

The catlas, computed with r=3, is available for download
[here](http://spacegraphcats.ucdavis.edu.s3.amazonaws.com/15genome.3.catlas.tar.gz).  To download and unpack it:

    curl -O http://spacegraphcats.ucdavis.edu.s3.amazonaws.com/15genome.3.catlas.tar.gz
    tar xzf 15genome.3.catlas.tar.gz
    
This creates the `15genome` directory.  The signatures are available within
the directory as `15genome/15genome.fa.gz.sig`.

To run against the entire set of signatures, do:

    ./search-for-domgraph-nodes.py 15genome 3 15genome/15genome.fa.gz.sig
    
Add `--append-csv out.csv` to get the output in spreadsheet form.

## mircea

The `mircea` data set contains all 63 genomes used to build the mock
community data set in the
[Shakya et al., 2014](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3665634/)
paper.  The full collection of genomes is available for download in
FASTA
[here](http://spacegraphcats.ucdavis.edu.s3.amazonaws.com/mircea.fa.gz).
(The senior author's name is "Mircea Podar", which is where the data
set name comes from.)

To download and unpack,

    curl -O http://spacegraphcats.ucdavis.edu.s3.amazonaws.com/mircea.tar.gz
    tar xzf mircea.tar.gz

The data set contains catlases at radius 3 and radius 5; to benchmark, do:

    ./search-for-domgraph-nodes.py mircea 3 mircea/mircea.all.sig

### Constructing `mircea`

We built 'mircea' like so:

    cats-in-practice/pipeline/make-genome-catlas.py mircea mircea.fa -M 6e9

which runs:

    ./walk-dbg.py -k 31 -M 6e9 -o mircea mircea.fa --label
    ./build-catlas.py mircea 3 --no-merge-mxt
    ./merge-mxt-in-memory.py mircea 3

We then also computed the catlas for radius 5, so:

    ./build-catlas.py mircea 5 --no-merge-mxt
    ./merge-mxt-in-memory.py mircea 5

The signatures were computed with:

    sourmash compute -k 31 --dna --singleton mircea.fa -o mircea/mircea.all.sig

## hu_catlas

The `hu_catlas` contains the cDBG files (`hu_catlas.gxt` and
`hu_catlas.mxt`) for the two smallest data sets from
[Hu et al., 2016](http://mbio.asm.org/content/7/1/e01669-15.full).
You can download it
[here](http://spacegraphcats.ucdavis.edu.s3.amazonaws.com/hu_catlas.tar.gz).

This is one of the smallest "real" data sets we have.  Nonetheless the
cDBG is quite large: the cDBG has 54583987 vertices, 64166942 edges
and 302412 components (according to `build-catlas.py`).

To run,

    curl -O http://spacegraphcats.ucdavis.edu.s3.amazonaws.com/hu_catlas.tar.gz
    tar xzf hu_catlas.tar.gz
    ./build-catlas.py hu_catlas 5 --no-merge-mxt

Currently the last command requires about 65 GB of RAM and fails to complete
in 100 hours.  I have not been able to recover any output showing where it
gets stuck, but no files are created (e.g. no aug files).

### Constructing `hu_catlas`

We used the following commands:

    # error trim the two data sets
    interleave-reads.py SRR1976948_1.fastq.gz SRR1976948_2.fastq.gz | \
        trim-low-abund.py -k 21 -V -Z 18 -C 3 -M 12e9 -o - - | \
        gzip -9c > SRR1976948.abundtrim.fq.gz
        
    interleave-reads.py SRR1977249_1.fastq.gz SRR1977249_2.fastq.gz | \
        trim-low-abund.py -k 21 -V -Z 18 -C 3 -M 12e9 -o - - | \
        gzip -9c > SRR1977249.abundtrim.fq.gz 
        
    for i in *.fq.gz; do 
        extract-paired-reads.py $i -p $i.pe.gz -s /dev/null --gzip;
    done

    load-graph.py -M 6e9 -k 31 --no-build-tagset hu_abundtrim.ng \
        SRR1976948.abundtrim.fq.gz SRR1977249.abundtrim.fq.gz

    /home/ubuntu/spacegraphcats/walk-dbg.py -o hu_catlas -l hu_abundtrim.ng \
        SRR1976948.abundtrim.fq.gz SRR1977249.abundtrim.fq.gz

## Appendices

### Appendix: Installing the requirements

Starting from a blank Ubuntu 15.10 install, add some packages:

    sudo apt-get update && sudo apt-get -y install python3.5-dev \
       python3-virtualenv python3-matplotlib python3-numpy g++ make
       
Create a new virtualenv:

    cd
    python3.5 -m virtualenv env -p python3.5 --system-site-packages
    . env/bin/activate

Install many things:

    pip install screed pytest PyYAML
    pip install git+https://github.com/dib-lab/khmer.git
    pip install git+https://github.com/dib-lab/sourmash.git

Now clone and install spacegraphcats:

    git clone https://github.com/spacegraphcats/spacegraphcats

and run the tests to be sure:

    cd spacegraphcats
    make test
    
You should be done!

## Appendix: Updating the software

The two most likely packages for updates will be khmer and sourmash.  To
update, run these commands from within the virtualenv:

    pip install git+https://github.com/dib-lab/khmer.git
    pip install git+https://github.com/dib-lab/sourmash.git