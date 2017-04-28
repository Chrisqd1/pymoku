@0xc6a6e02be7124911;

struct LIHeader {
	instrumentId	@0 :Int8;
	instrumentVer	@1 :Int16;
	timeStep		@2 :Float64;
	startTime		@3 :Int64;
	startOffset		@4 :Float64;

	struct Channel {
		number		@0 :Int8;
		calibration	@1 :Float64;

		recordFmt	@2 :Text;
		procFmt		@3 :Text;
	}
	channels		@5 :List(Channel);

	csvFmt			@6 :Text;
	csvHeader		@7 :Text;
}

struct LIData {
	channel			@0 :Int8;
	data			@1 :Data;
}

struct LIFileElement {
	union {
		header		@0 :LIHeader;
		data		@1 :LIData;
	}
}
